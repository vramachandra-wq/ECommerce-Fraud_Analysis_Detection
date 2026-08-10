from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import execute_batch
import psycopg2

from api.auth import get_current_session, require_page
from auth.analyst_auth import PAGE_ADMIN_PANEL, ROLE_ADMIN
from auth.passwords import hash_password
from auth.sso import sync_keycloak_user
from config import DB_CONFIG
from fraud_engine.engine import clear_metadata_cache
from fraud_engine.rules import clear_interval_cache
from utils.blacklist_actions import blacklist_entity_from_order
from utils.system_audit import actor_from_session, log_system_event
from utils.time_utils import utcnow_naive

router = APIRouter()


class AnalystCreate(BaseModel):
    analyst_id: str
    employee_name: str
    username: str
    password: str
    role: str
    actor_role: Optional[str] = None


class BlacklistRequest(BaseModel):
    reason: str
    blacklisted_by: str = ""


class IPBlacklist(BlacklistRequest):
    ip_address: str


class PhoneBlacklist(BlacklistRequest):
    phone_number: str


class EmailBlacklist(BlacklistRequest):
    email: str


class BlacklistFromOrder(BaseModel):
    order_id: str
    entity_type: str
    reason: str
    blacklisted_by: str = ""


class WhitelistRequest(BaseModel):
    blacklist_id: int
    removed_by: str = ""
    removed_at: str


class BulkPermissionUpdate(BaseModel):
    analyst_id: str
    permissions: Dict[str, bool]
    granted_by: str = ""


class RuleUpdate(BaseModel):
    rule_id: str
    action: str
    threshold_value: Optional[float] = None
    time_interval_value: Optional[int] = None
    time_interval_unit: Optional[str] = None
    delay_minutes: Optional[int] = None


def _fetch_rule_snapshot(cur, rule_id: str) -> Optional[Dict[str, Any]]:
    cur.execute(
        """
        SELECT rule_id, rule_name, action, threshold_value, time_interval_value,
               time_interval_unit, delay_minutes
        FROM master.rule_master
        WHERE rule_id = %s
        """,
        (rule_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "rule_id": row[0],
        "rule_name": row[1],
        "action": row[2],
        "threshold_value": float(row[3]) if row[3] is not None else None,
        "time_interval_value": row[4],
        "time_interval_unit": row[5],
        "delay_minutes": row[6],
    }


def _require_admin_panel(
    session: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
) -> Dict[str, Any]:
    return session


@router.post("/create-analyst")
def create_analyst(
    data: AnalystCreate,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    actor = session["analyst"]
    if data.role == ROLE_ADMIN and not session.get("is_admin"):
        log_system_event(
            action="ANALYST_CREATE",
            **actor_from_session(session),
            resource_type="analyst",
            resource_id=data.analyst_id,
            outcome="denied",
            details={"role": data.role, "reason": "Only Admin can create Admin"},
            request_path="/create-analyst",
        )
        raise HTTPException(
            status_code=403,
            detail="Only Admin users can create Admin accounts.",
        )

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO master.analyst_users
                    (analyst_id, employee_name, username, password, role)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        data.analyst_id,
                        data.employee_name,
                        data.username,
                        hash_password(data.password),
                        data.role,
                    ),
                )
                synced, sync_error = sync_keycloak_user(
                    username=data.username,
                    password=data.password,
                    employee_name=data.employee_name,
                )
                if not synced:
                    conn.rollback()
                    log_system_event(
                        action="ANALYST_CREATE",
                        **actor_from_session(session),
                        resource_type="analyst",
                        resource_id=data.analyst_id,
                        outcome="failure",
                        details={
                            "username": data.username,
                            "role": data.role,
                            "reason": "keycloak_sync_failed",
                            "error": sync_error,
                        },
                        request_path="/create-analyst",
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "Analyst was not created because Keycloak sync failed: "
                            f"{sync_error}"
                        ),
                    )
                log_system_event(
                    cur,
                    action="ANALYST_CREATE",
                    **actor_from_session(session),
                    resource_type="analyst",
                    resource_id=data.analyst_id,
                    details={
                        "username": data.username,
                        "role": data.role,
                        "created_by": actor["analyst_id"],
                        "keycloak_synced": True,
                    },
                    request_path="/create-analyst",
                )
                conn.commit()
        return {"message": f"Analyst {data.employee_name} Created"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blacklist-from-order")
def blacklist_from_order(
    data: BlacklistFromOrder,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    blacklisted_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                entity, value = blacklist_entity_from_order(
                    cur,
                    order_id=data.order_id,
                    entity_type=data.entity_type,
                    reason=data.reason,
                    blacklisted_by=blacklisted_by,
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_ADD",
                    **actor_from_session(session),
                    resource_type=entity,
                    resource_id=data.order_id,
                    details={"entity_type": entity, "reason": data.reason, "via": "order"},
                    request_path="/blacklist-from-order",
                )
                conn.commit()
        return {"message": f"{entity.upper()} blacklisted from order {data.order_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blacklist-ip")
def blacklist_ip(
    data: IPBlacklist,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    blacklisted_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO master.ip_blacklist (ip_address, reason, blacklisted_by)
                    VALUES (%s,%s,%s)
                    """,
                    (data.ip_address, data.reason, blacklisted_by),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_ADD",
                    **actor_from_session(session),
                    resource_type="ip",
                    resource_id=data.ip_address,
                    details={"reason": data.reason},
                    request_path="/blacklist-ip",
                )
        return {"message": "IP Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-ip")
def whitelist_ip(
    data: WhitelistRequest,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    removed_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.ip_blacklist
                    SET is_active = FALSE,
                        removed_by = %s,
                        removed_at = %s
                    WHERE blacklist_id = %s
                    """,
                    (removed_by, data.removed_at, data.blacklist_id),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_REMOVE",
                    **actor_from_session(session),
                    resource_type="ip",
                    resource_id=str(data.blacklist_id),
                    request_path="/whitelist-ip",
                )
        return {"message": "IP Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blacklist-phone")
def blacklist_phone(
    data: PhoneBlacklist,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    blacklisted_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO master.phone_blacklist (phone_number, reason, blacklisted_by)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (phone_number) DO UPDATE SET
                        is_active = TRUE,
                        reason = EXCLUDED.reason,
                        blacklisted_by = EXCLUDED.blacklisted_by,
                        blacklisted_at = CURRENT_TIMESTAMP
                    """,
                    (data.phone_number, data.reason, blacklisted_by),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_ADD",
                    **actor_from_session(session),
                    resource_type="phone",
                    resource_id=data.phone_number,
                    details={"reason": data.reason},
                    request_path="/blacklist-phone",
                )
        return {"message": "Phone Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-phone")
def whitelist_phone(
    data: WhitelistRequest,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    removed_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.phone_blacklist
                    SET is_active = FALSE,
                        removed_by = %s,
                        removed_at = %s
                    WHERE blacklist_id = %s
                    """,
                    (removed_by, data.removed_at, data.blacklist_id),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_REMOVE",
                    **actor_from_session(session),
                    resource_type="phone",
                    resource_id=str(data.blacklist_id),
                    request_path="/whitelist-phone",
                )
        return {"message": "Phone Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blacklist-email")
def blacklist_email(
    data: EmailBlacklist,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    blacklisted_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO master.email_blacklist (email, reason, blacklisted_by)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (email) DO UPDATE SET
                        is_active = TRUE,
                        reason = EXCLUDED.reason,
                        blacklisted_by = EXCLUDED.blacklisted_by,
                        blacklisted_at = CURRENT_TIMESTAMP
                    """,
                    (data.email, data.reason, blacklisted_by),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_ADD",
                    **actor_from_session(session),
                    resource_type="email",
                    resource_id=data.email,
                    details={"reason": data.reason},
                    request_path="/blacklist-email",
                )
        return {"message": "Email Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-email")
def whitelist_email(
    data: WhitelistRequest,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    removed_by = session["analyst"]["analyst_id"]
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE master.email_blacklist
                    SET is_active = FALSE,
                        removed_by = %s,
                        removed_at = %s
                    WHERE blacklist_id = %s
                    """,
                    (removed_by, data.removed_at, data.blacklist_id),
                )
                log_system_event(
                    cur,
                    action="BLACKLIST_REMOVE",
                    **actor_from_session(session),
                    resource_type="email",
                    resource_id=str(data.blacklist_id),
                    request_path="/whitelist-email",
                )
        return {"message": "Email Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/permissions/bulk")
def update_permissions_bulk(
    payload: BulkPermissionUpdate,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    timestamp = utcnow_naive()
    granted_by = session["analyst"]["analyst_id"]
    data_to_insert = [
        (payload.analyst_id, page_key, granted, granted_by, timestamp)
        for page_key, granted in payload.permissions.items()
    ]

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                execute_batch(
                    cur,
                    """
                    INSERT INTO master.analyst_permissions
                    (analyst_id, page_key, granted, granted_by, granted_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (analyst_id, page_key)
                    DO UPDATE SET
                        granted = EXCLUDED.granted,
                        granted_by = EXCLUDED.granted_by,
                        granted_at = EXCLUDED.granted_at
                    """,
                    data_to_insert,
                )
                log_system_event(
                    cur,
                    action="PERMISSIONS_UPDATE",
                    **actor_from_session(session),
                    resource_type="analyst",
                    resource_id=payload.analyst_id,
                    details={"permissions": payload.permissions},
                    request_path="/permissions/bulk",
                )
        return {"message": f"Successfully updated {len(payload.permissions)} permissions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update-rule")
def update_rule(
    data: RuleUpdate,
    session: Dict[str, Any] = Depends(_require_admin_panel),
):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                before = _fetch_rule_snapshot(cur, data.rule_id)
                if not before:
                    raise HTTPException(status_code=404, detail="Rule not found")
                if data.rule_id == "R001":
                    if data.delay_minutes is None or data.delay_minutes <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail="R001 requires a positive delay_minutes value.",
                        )
                    # R001 is always HOLD — only delay_minutes is editable.
                    cur.execute(
                        """
                        UPDATE master.rule_master
                        SET action = 'HOLD',
                            threshold_value = %s,
                            time_interval_value = NULL,
                            time_interval_unit = NULL,
                            delay_minutes = %s
                        WHERE rule_id = %s
                        """,
                        (
                            data.threshold_value,
                            data.delay_minutes,
                            data.rule_id,
                        ),
                    )
                else:
                    delay = data.delay_minutes
                    if delay is not None and delay <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail="delay_minutes must be a positive integer.",
                        )
                    if delay is None:
                        cur.execute(
                            """
                            UPDATE master.rule_master
                            SET action = %s,
                                threshold_value = %s,
                                time_interval_value = %s,
                                time_interval_unit = %s
                            WHERE rule_id = %s
                            """,
                            (
                                data.action,
                                data.threshold_value,
                                data.time_interval_value,
                                data.time_interval_unit,
                                data.rule_id,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE master.rule_master
                            SET action = %s,
                                threshold_value = %s,
                                time_interval_value = %s,
                                time_interval_unit = %s,
                                delay_minutes = %s
                            WHERE rule_id = %s
                            """,
                            (
                                data.action,
                                data.threshold_value,
                                data.time_interval_value,
                                data.time_interval_unit,
                                delay,
                                data.rule_id,
                            ),
                        )

                after = _fetch_rule_snapshot(cur, data.rule_id)
                log_system_event(
                    cur,
                    action="RULE_UPDATE",
                    **actor_from_session(session),
                    resource_type="rule",
                    resource_id=data.rule_id,
                    details={
                        "before": before,
                        "after": after,
                        "changes": {
                            key: {
                                "before": before.get(key),
                                "after": after.get(key) if after else None,
                            }
                            for key in (
                                "action",
                                "threshold_value",
                                "time_interval_value",
                                "time_interval_unit",
                                "delay_minutes",
                            )
                            if before.get(key) != (after.get(key) if after else None)
                        },
                    },
                    request_path="/update-rule",
                )

        clear_interval_cache(data.rule_id)
        clear_metadata_cache(data.rule_id)
        return {"message": f"Rule {data.rule_id} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
