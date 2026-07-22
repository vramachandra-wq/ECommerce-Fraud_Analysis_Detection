from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch
from config import DB_CONFIG
from auth.analyst_auth import ROLE_ADMIN
from auth.passwords import hash_password

# Note: Adjust these import paths as needed
from fraud_engine.rules import clear_interval_cache
from fraud_engine.engine import clear_metadata_cache

router = APIRouter()


# --- PYDANTIC MODELS ---

class AnalystCreate(BaseModel):
    analyst_id: str
    employee_name: str
    username: str
    password: str
    role: str
    actor_role: Optional[str] = None

class BlacklistRequest(BaseModel):
    reason: str
    blacklisted_by: str

class IPBlacklist(BlacklistRequest):
    ip_address: str

class PhoneBlacklist(BlacklistRequest):
    phone_number: str

class EmailBlacklist(BlacklistRequest):
    email: str

class WhitelistRequest(BaseModel):
    blacklist_id: int
    removed_by: str
    removed_at: str

class BulkPermissionUpdate(BaseModel):
    analyst_id: str
    permissions: Dict[str, bool]
    granted_by: str

class RuleUpdate(BaseModel):
    rule_id: str
    action: str
    threshold_value: Optional[float] = None
    time_interval_value: Optional[int] = None
    time_interval_unit: Optional[str] = None
    delay_minutes: Optional[int] = None


# --- ANALYST ENDPOINTS ---

@router.post("/create-analyst")
def create_analyst(data: AnalystCreate):
    if data.role == ROLE_ADMIN and data.actor_role != ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Only Admin users can create Admin accounts.",
        )

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
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
        return {"message": f"Analyst {data.employee_name} Created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- IP BLACKLIST ENDPOINTS ---

@router.post("/blacklist-ip")
def blacklist_ip(data: IPBlacklist):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO master.ip_blacklist (ip_address, reason, blacklisted_by)
                    VALUES (%s,%s,%s)
                    """,
                    (data.ip_address, data.reason, data.blacklisted_by),
                )
        return {"message": "IP Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-ip")
def whitelist_ip(data: WhitelistRequest):
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
                    (data.removed_by, data.removed_at, data.blacklist_id),
                )
        return {"message": "IP Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- PHONE BLACKLIST ENDPOINTS ---

@router.post("/blacklist-phone")
def blacklist_phone(data: PhoneBlacklist):
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
                    (data.phone_number, data.reason, data.blacklisted_by),
                )
        return {"message": "Phone Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-phone")
def whitelist_phone(data: WhitelistRequest):
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
                    (data.removed_by, data.removed_at, data.blacklist_id),
                )
        return {"message": "Phone Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- EMAIL BLACKLIST ENDPOINTS ---

@router.post("/blacklist-email")
def blacklist_email(data: EmailBlacklist):
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
                    (data.email, data.reason, data.blacklisted_by),
                )
        return {"message": "Email Blacklisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/whitelist-email")
def whitelist_email(data: WhitelistRequest):
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
                    (data.removed_by, data.removed_at, data.blacklist_id),
                )
        return {"message": "Email Whitelisted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- PERMISSIONS AND RULES ---

@router.put("/permissions/bulk")
def update_permissions_bulk(payload: BulkPermissionUpdate):
    timestamp = datetime.now()
    
    # Prepare list of tuples for batch execution
    data_to_insert = [
        (payload.analyst_id, page_key, granted, payload.granted_by, timestamp)
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
                    data_to_insert
                )
        return {"message": f"Successfully updated {len(payload.permissions)} permissions."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update-rule")
def update_rule(data: RuleUpdate):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # R001: delay_minutes is the only editable timing field
                if data.rule_id == "R001":
                    if data.delay_minutes is None or data.delay_minutes <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail="R001 requires a positive delay_minutes value.",
                        )
                    cur.execute(
                        """
                        UPDATE master.rule_master
                        SET action = %s,
                            threshold_value = %s,
                            time_interval_value = NULL,
                            time_interval_unit = NULL,
                            delay_minutes = %s
                        WHERE rule_id = %s
                        """,
                        (
                            data.action,
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

        clear_interval_cache(data.rule_id)
        clear_metadata_cache(data.rule_id)

        return {"message": f"Rule {data.rule_id} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Backend Error updating rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
