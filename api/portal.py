"""Portal API for the React analyst frontend."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from api.auth import (
    authenticate_credentials,
    get_analyst_by_id,
    get_current_session,
    get_session_by_username,
    PORTAL_SESSION_COOKIE,
    require_page,
    verify_session_token,
)
from api.cookie_utils import clear_portal_cookie, portal_cookie_kwargs
from auth.login_guard import client_key, login_guard
from config import (
    DB_CONFIG,
    PORTAL_TOKEN_TTL,
    POWER_BI_EMBED_URL,
    SSO_DEFAULT_RETURN_TO,
    is_groq_api_key_configured,
)
from database.connection import get_cursor
from auth.analyst_auth import (
    ALL_PAGES,
    PAGE_ADMIN_PANEL,
    PAGE_AI_CHATBOT,
    PAGE_FRAUD_DASHBOARD,
    PAGE_LABELS,
    PAGE_POWER_BI,
    change_analyst_password,
)
from auth.sso import (
    append_query_param,
    build_authorize_url,
    build_logout_url,
    complete_sso_login,
    create_oauth_state,
    create_pkce_pair,
    normalize_return_to,
    parse_oauth_state,
    sso_is_configured,
    sync_keycloak_password,
)
from ui.i18n import TRANSLATIONS
import psycopg2

KC_ID_COOKIE = "metro_cart_kc_id"
SSO_HANDOFF_COOKIE = "metro_cart_sso_handoff"
SSO_HANDOFF_TTL_SECONDS = 120
from api.scheduler import get_auto_approval_status
from fraud_engine.auto_approval import sync_expired_holds
from fraud_engine.backlog import (
    compute_deadline,
    detect_backlog_orders,
    fetch_review_queue_with_delay,
    get_applicable_delay_minutes,
    get_backlog_stats,
)
from utils.queries import (
    get_active_blacklist_entry,
    get_active_email_blacklist_entry,
    get_active_phone_blacklist_entry,
    get_all_rules,
    get_analyst_performance,
    get_dashboard_order_trend,
    get_kpis,
    get_order_detail,
    get_orders_over_time,
    get_permission_matrix,
    get_recent_orders,
    get_review_audit_log,
    get_rule_stats,
)
from utils.pii import sanitize_pii_record
from utils.blacklist_actions import blacklist_entity_from_order
from utils.time_utils import utcnow_naive
from utils.system_audit import actor_from_session, log_system_event, read_audit_logs

router = APIRouter()


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # numpy / pandas scalars
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass
    return value


def _df_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    return jsonable_records(df)


def jsonable_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = df.to_dict(orient="records")
    cleaned: List[Dict[str, Any]] = []
    for row in records:
        cleaned.append({key: _json_value(value) for key, value in row.items()})
    return cleaned


def _jsonable_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: _json_value(value) for key, value in data.items()}


def _order_timing(cur: Any, order: Dict[str, Any]) -> Dict[str, Any]:
    """Live delay / remaining / overdue fields for a single queue order."""
    order_id = str(order.get("order_id") or "")
    delay_minutes = get_applicable_delay_minutes(cur, order_id)
    tagged = order.get("order_timestamp")
    if tagged is None:
        return {
            "delay_minutes": delay_minutes,
            "review_deadline": None,
            "minutes_remaining": None,
            "minutes_remaining_display": 0.0,
            "minutes_overdue": 0.0,
            "is_overdue": False,
            "rule_name": order.get("flagged_reason"),
        }
    if hasattr(tagged, "tzinfo") and tagged.tzinfo is not None:
        tagged_naive = tagged.replace(tzinfo=None)
    else:
        tagged_naive = tagged

    now = utcnow_naive()
    deadline = compute_deadline(tagged_naive, delay_minutes)
    remaining = (deadline - now).total_seconds() / 60.0
    return {
        "delay_minutes": delay_minutes,
        "review_deadline": deadline,
        "minutes_remaining": remaining,
        "minutes_remaining_display": max(0.0, remaining),
        "minutes_overdue": abs(remaining) if remaining <= 0 else 0.0,
        "is_overdue": remaining <= 0,
        "rule_name": order.get("flagged_reason"),
    }


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    username: str = ""
    current_password: str
    new_password: str
    confirm_password: str


class ChatMessage(BaseModel):
    role: str
    content: str
    # Kept client-side for follow-up context; never shown in the portal UI.
    sql: str | None = None
    df: List[Dict[str, Any]] | None = None


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class OrderBlacklistRequest(BaseModel):
    entity_type: str  # ip | phone | email
    reason: str


def _message_for_key(key: str) -> str:
    entry = TRANSLATIONS.get(key) or {}
    return entry.get("en") or key


def _client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return ""


def _raise_if_locked(guard_key: str) -> None:
    status = login_guard.status(guard_key)
    if status.locked:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed login attempts. "
                f"Try again in {status.retry_after_seconds} seconds."
            ),
            headers={"Retry-After": str(status.retry_after_seconds)},
        )


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request):
    username = payload.username.strip()
    guard_key = client_key(username, _client_ip(request))
    _raise_if_locked(guard_key)

    session = authenticate_credentials(username, payload.password)
    if not session:
        lock = login_guard.record_failure(guard_key)
        log_system_event(
            action="AUTH_LOGIN",
            actor_type="analyst",
            actor_id=username,
            outcome="failure",
            details={
                "reason": "invalid_credentials",
                "failure_count": lock.failure_count,
                "locked": lock.locked,
            },
            request_path="/auth/login",
        )
        if lock.locked:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many failed login attempts. "
                    f"Try again in {lock.retry_after_seconds} seconds."
                ),
                headers={"Retry-After": str(lock.retry_after_seconds)},
            )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    login_guard.clear(guard_key)
    log_system_event(
        action="AUTH_LOGIN",
        **actor_from_session(session),
        outcome="success",
        request_path="/auth/login",
    )
    response = JSONResponse(content=session)
    response.set_cookie(
        key=PORTAL_SESSION_COOKIE,
        value=session["token"],
        **portal_cookie_kwargs(max_age=PORTAL_TOKEN_TTL),
    )
    # Password login must not keep a prior SSO id_token around; otherwise logout
    # would incorrectly redirect into Keycloak for a local session.
    clear_portal_cookie(response, KC_ID_COOKIE)
    clear_portal_cookie(response, SSO_HANDOFF_COOKIE)
    return response


@router.post("/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
    portal_session: Optional[str] = Cookie(None, alias=PORTAL_SESSION_COOKIE),
):
    """Change password from login screen (username) or while logged in (Bearer)."""
    analyst_id = ""
    username = (payload.username or "").strip()

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif portal_session:
        token = portal_session.strip()
    if token:
        subject = verify_session_token(token)
        if subject and not str(subject).startswith("customer:"):
            analyst_id = str(subject)
            username = ""

    if not analyst_id and not username:
        raise HTTPException(
            status_code=400,
            detail=_message_for_key("password_change_missing_fields"),
        )

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            ok, message_key = change_analyst_password(
                cur,
                conn,
                analyst_id=analyst_id,
                username=username,
                current_password=payload.current_password,
                new_password=payload.new_password,
                confirm_password=payload.confirm_password,
            )
            if ok:
                resolved_username = username
                if analyst_id and not resolved_username:
                    cur.execute(
                        """
                        SELECT username
                        FROM master.analyst_users
                        WHERE analyst_id = %s
                        """,
                        (analyst_id,),
                    )
                    row = cur.fetchone()
                    resolved_username = str((row or [""])[0] or "").strip()
                synced, sync_error = sync_keycloak_password(
                    resolved_username,
                    payload.new_password,
                )
                if not synced:
                    conn.rollback()
                    raise HTTPException(
                        status_code=502,
                        detail=f"Password change was rolled back because SSO password sync failed: {sync_error}",
                    )
                conn.commit()

    if not ok:
        status = 404 if message_key == "password_change_user_not_found" else 400
        raise HTTPException(status_code=status, detail=_message_for_key(message_key))

    log_system_event(
        action="AUTH_PASSWORD_CHANGE",
        actor_type="analyst",
        actor_id=analyst_id or username,
        outcome="success",
        request_path="/auth/change-password",
    )
    return {
        "message": _message_for_key("password_change_success"),
        "message_key": "password_change_success",
    }

@router.get("/auth/sso/config")
def sso_config():
    """Public flag so the login UI can show/hide the SSO button."""
    return {"enabled": sso_is_configured()}


@router.get("/auth/sso/login")
def sso_login(return_to: Optional[str] = Query(None)):
    if not sso_is_configured():
        raise HTTPException(status_code=503, detail="SSO is not configured")
    destination = normalize_return_to(return_to)
    code_verifier, code_challenge = create_pkce_pair()
    state = create_oauth_state(destination, code_verifier=code_verifier)
    return RedirectResponse(
        url=build_authorize_url(state=state, code_challenge=code_challenge),
        status_code=302,
    )


@router.get("/auth/sso/callback")
def sso_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """OIDC callback: map Keycloak user → local analyst session, then redirect."""
    parsed_state = parse_oauth_state(state or "")
    return_to = normalize_return_to((parsed_state or {}).get("return_to"))

    def _fail(reason: str, actor_id: str = "") -> RedirectResponse:
        log_system_event(
            action="AUTH_LOGIN",
            actor_type="analyst",
            actor_id=actor_id or "sso",
            outcome="failure",
            details={"reason": reason, "method": "sso"},
            request_path="/auth/sso/callback",
        )
        return RedirectResponse(
            url=append_query_param(return_to, "sso_error", reason),
            status_code=302,
        )

    if not sso_is_configured():
        return _fail("sso_not_configured")
    if error:
        return _fail(error_description or error)
    if not code or not parsed_state:
        return _fail("invalid_sso_callback")

    code_verifier = str(parsed_state.get("code_verifier") or "")
    username, id_token, exchange_error = complete_sso_login(
        code, code_verifier=code_verifier
    )
    if exchange_error or not username:
        return _fail(exchange_error or "sso_exchange_failed")

    session = get_session_by_username(username)
    if not session:
        return _fail("no_local_analyst", actor_id=username)

    log_system_event(
        action="AUTH_LOGIN",
        **actor_from_session(session),
        outcome="success",
        details={"method": "sso"},
        request_path="/auth/sso/callback",
    )
    response = RedirectResponse(
        url=append_query_param(return_to, "sso", "1"),
        status_code=302,
    )
    response.set_cookie(
        key=SSO_HANDOFF_COOKIE,
        value=session["token"],
        **portal_cookie_kwargs(max_age=SSO_HANDOFF_TTL_SECONDS),
    )
    if id_token:
        response.set_cookie(
            key=KC_ID_COOKIE,
            value=id_token,
            **portal_cookie_kwargs(max_age=PORTAL_TOKEN_TTL),
        )
    return response


@router.get("/auth/sso/complete")
def sso_complete(
    metro_cart_sso_handoff: Optional[str] = Cookie(None, alias=SSO_HANDOFF_COOKIE),
):
    """
    One-time SSO handoff: exchange the short-lived HttpOnly cookie for a
    normal portal session payload (same shape as /auth/login).
    """
    token = (metro_cart_sso_handoff or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="SSO session handoff missing or expired")

    analyst_id = verify_session_token(token)
    if not analyst_id or str(analyst_id).startswith("customer:"):
        raise HTTPException(status_code=401, detail="Invalid SSO session handoff")

    profile = get_analyst_by_id(str(analyst_id))
    if not profile:
        raise HTTPException(status_code=401, detail="User not found")

    payload = {
        "analyst": profile["analyst"],
        "granted_pages": profile["granted_pages"],
        "is_admin": profile["is_admin"],
        "token": token,
    }
    response = JSONResponse(content=payload)
    response.set_cookie(
        key=PORTAL_SESSION_COOKIE,
        value=token,
        **portal_cookie_kwargs(max_age=PORTAL_TOKEN_TTL),
    )
    clear_portal_cookie(response, SSO_HANDOFF_COOKIE)
    return response


def _clear_auth_cookies(response) -> None:
    clear_portal_cookie(response, KC_ID_COOKIE)
    clear_portal_cookie(response, PORTAL_SESSION_COOKIE)
    clear_portal_cookie(response, SSO_HANDOFF_COOKIE)


@router.get("/auth/logout")
@router.post("/auth/logout")
def logout(
    return_to: Optional[str] = Query(None),
    metro_cart_kc_id: Optional[str] = Cookie(None, alias=KC_ID_COOKIE),
):
    """
    End the local portal session. If an SSO id_token cookie is present and
    Keycloak is configured, also end the IdP session; otherwise redirect home.
    """
    destination = normalize_return_to(return_to or SSO_DEFAULT_RETURN_TO)

    if sso_is_configured() and metro_cart_kc_id:
        logout_url = build_logout_url(
            post_logout_redirect_uri=destination,
            id_token_hint=metro_cart_kc_id,
        )
        response = RedirectResponse(url=logout_url, status_code=302)
        _clear_auth_cookies(response)
        return response

    response = RedirectResponse(url=destination, status_code=302)
    _clear_auth_cookies(response)
    return response


@router.get("/auth/sso/logout")
def sso_logout(
    return_to: Optional[str] = Query(None),
    metro_cart_kc_id: Optional[str] = Cookie(None, alias=KC_ID_COOKIE),
):
    """
    Backward-compatible alias for `/auth/logout` (SSO-aware cookie clear).
    Local password sessions without a Keycloak id_token just redirect home.
    """
    return logout(return_to=return_to, metro_cart_kc_id=metro_cart_kc_id)


@router.get("/auth/me")
def me(session: Dict[str, Any] = Depends(get_current_session)):
    return session


@router.get("/portal/config")
def portal_config(session: Dict[str, Any] = Depends(get_current_session)):
    return {
        "page_labels": PAGE_LABELS,
        "all_pages": ALL_PAGES,
        "power_bi_embed_url": POWER_BI_EMBED_URL,
        "granted_pages": session["granted_pages"],
        "groq_configured": is_groq_api_key_configured(),
    }


@router.post("/portal/sync-holds")
def sync_holds(_: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    with get_cursor(commit=True) as (conn, cur):
        count = sync_expired_holds(conn, cur)
    return {"auto_approved": count}


@router.get("/portal/scheduler-status")
def scheduler_status(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    """Expose auto-approval scheduler heartbeat for Admin visibility."""
    return {"scheduler": get_auto_approval_status()}


@router.get("/portal/queue")
def queue(_: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    """Review queue with Streamlit-parity delay / remaining / overdue fields."""
    with get_cursor() as (_, cur):
        df = fetch_review_queue_with_delay(cur)
        backlog_stats = get_backlog_stats(cur)
    rows = _df_records(df)
    pending = sum(1 for r in rows if r.get("order_status") == "PENDING_REVIEW")
    on_hold = sum(1 for r in rows if r.get("order_status") == "ON_HOLD")
    return {
        "orders": rows,
        "metrics": {
            "total": len(rows),
            "pending_review": pending,
            "on_hold": on_hold,
            "backlog": int(backlog_stats.get("total_backlog") or 0),
            "max_minutes_overdue": float(backlog_stats.get("max_minutes_overdue") or 0),
        },
        "backlog": _jsonable_dict(backlog_stats),
    }


@router.get("/portal/dashboard/statistics")
def dashboard_statistics(
    period: str = "month",
    _: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD)),
):
    """Actionable order-volume trend for Fraud Dashboard Statistics chart."""
    with get_cursor() as (_, cur):
        trend = get_dashboard_order_trend(cur, period)
    return {
        "period": trend["period"],
        "granularity": trend["granularity"],
        "totals": trend["totals"],
        "points": [_jsonable_dict(p) for p in trend["points"]],
    }


@router.get("/portal/backlog")
def backlog(_: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    """Overdue ON_HOLD / PENDING_REVIEW orders (past delay_minutes window)."""
    with get_cursor() as (_, cur):
        df = detect_backlog_orders(cur)
        stats = get_backlog_stats(cur)
    return {"orders": _df_records(df), "stats": _jsonable_dict(stats)}


@router.get("/portal/orders/recent")
def recent_orders_list(
    limit: int = Query(50, ge=1, le=200),
    _: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
):
    """Latest orders across all statuses (shop checkouts appear here even when APPROVED)."""
    with get_cursor() as (_, cur):
        from database.order_items import ensure_order_items_table

        try:
            ensure_order_items_table(cur)
        except Exception:
            pass
        df = get_recent_orders(cur, limit=limit)
    return {"orders": _df_records(df)}


@router.get("/portal/orders/{order_id}")
def order_detail(
    order_id: str,
    session: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD)),
):
    analyst = session.get("analyst") or {}
    with get_cursor() as (_, cur):
        order = get_order_detail(cur, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        # Lookups must use raw PII from DB before any masking for the client.
        ip_bl = get_active_blacklist_entry(cur, order["ip_address"])
        phone_bl = get_active_phone_blacklist_entry(cur, order.get("phone_number") or "")
        email_bl = get_active_email_blacklist_entry(cur, order.get("email") or "")
        timing = _order_timing(cur, order)

    safe_order = sanitize_pii_record(order, analyst)
    return {
        "order": _jsonable_dict(safe_order or {}),
        "timing": _jsonable_dict(timing),
        "blacklists": {
            "ip": _jsonable_dict(sanitize_pii_record(ip_bl, analyst) or {}) if ip_bl else None,
            "phone": (
                _jsonable_dict(sanitize_pii_record(phone_bl, analyst) or {}) if phone_bl else None
            ),
            "email": (
                _jsonable_dict(sanitize_pii_record(email_bl, analyst) or {}) if email_bl else None
            ),
        },
    }


@router.post("/portal/orders/{order_id}/blacklist")
def blacklist_order_entity(
    order_id: str,
    payload: OrderBlacklistRequest,
    session: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD)),
):
    """Blacklist IP/phone/email for an order without accepting raw PII from the client."""
    analyst = session.get("analyst") or {}
    analyst_id = analyst.get("analyst_id")
    if not analyst_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        with get_cursor(commit=True) as (_, cur):
            entity, _value = blacklist_entity_from_order(
                cur,
                order_id=order_id,
                entity_type=payload.entity_type,
                reason=payload.reason,
                blacklisted_by=analyst_id,
            )
            log_system_event(
                cur,
                action="BLACKLIST_ADD",
                **actor_from_session(session),
                resource_type=entity,
                resource_id=order_id,
                details={"entity_type": entity, "reason": payload.reason, "via": "portal_order"},
                request_path=f"/portal/orders/{order_id}/blacklist",
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"message": f"{entity.upper()} blacklisted from order {order_id}"}


@router.get("/portal/blacklist/{entity_type}/{value}")
def blacklist_lookup(
    entity_type: str,
    value: str,
    session: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
):
    analyst = session.get("analyst") or {}
    with get_cursor() as (_, cur):
        if entity_type == "ip":
            entry = get_active_blacklist_entry(cur, value)
        elif entity_type == "phone":
            entry = get_active_phone_blacklist_entry(cur, value)
        elif entity_type == "email":
            entry = get_active_email_blacklist_entry(cur, value)
        else:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    safe = sanitize_pii_record(entry, analyst) if entry else None
    return {"entry": _jsonable_dict(safe) if safe else None}


@router.get("/portal/analytics/summary")
def analytics_summary(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    with get_cursor() as (_, cur):
        kpis = get_kpis(cur)
        recent_df = get_recent_orders(cur)
        trend_df = get_orders_over_time(cur)
    total_orders = kpis["total_orders"]
    total_fraud = kpis["total_fraud"]
    fraud_rate = (total_fraud / total_orders * 100) if total_orders else 0
    return {
        "kpis": {
            **kpis,
            "fraud_rate": round(fraud_rate, 2),
        },
        "recent_orders": _df_records(recent_df),
        "orders_over_time": _df_records(trend_df),
    }


@router.get("/portal/analytics/rule-stats")
def rule_stats(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    with get_cursor() as (_, cur):
        df = get_rule_stats(cur)
    return {"rules": _df_records(df)}


@router.get("/portal/analytics/analyst-performance")
def analyst_performance(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    with get_cursor() as (_, cur):
        df = get_analyst_performance(cur)
    return {"analysts": _df_records(df)}


@router.get("/portal/permissions")
def permissions(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    with get_cursor() as (_, cur):
        analysts = get_permission_matrix(cur)
    serialized = []
    for analyst in analysts:
        serialized.append(
            {
                **analyst,
                "granted_pages": sorted(analyst.get("granted_pages", [])),
            }
        )
    return {"analysts": serialized, "all_pages": ALL_PAGES, "page_labels": PAGE_LABELS}


@router.get("/portal/rules")
def rules(_: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL))):
    with get_cursor() as (_, cur):
        rules_data = get_all_rules(cur)
    return {"rules": [_jsonable_dict(r) for r in rules_data]}


@router.get("/portal/audit")
def audit_log(
    limit: int = 100,
    offset: int = 0,
    order_id: str | None = None,
    _: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
):
    """Order review audit trail from master.order_review_audit."""
    with get_cursor() as (_, cur):
        payload = get_review_audit_log(
            cur,
            limit=limit,
            offset=offset,
            order_id=order_id.strip() if order_id else None,
        )
    entries = [_jsonable_dict(row) for row in payload["entries"]]
    return {
        "entries": entries,
        "total": payload["total"],
        "limit": payload["limit"],
        "offset": payload["offset"],
    }


@router.get("/portal/audit-logs")
def audit_logs(
    limit: int = 100,
    action: str | None = None,
    _: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
):
    """Recent system audit events from master.system_audit_log (admin only)."""
    with get_cursor() as (_, cur):
        rows = read_audit_logs(limit=limit, action=action, cur=cur)
    return {"logs": [_jsonable_dict(r) for r in rows]}


@router.get("/portal/power-bi")
def power_bi(_: Dict[str, Any] = Depends(require_page(PAGE_POWER_BI))):
    if not POWER_BI_EMBED_URL:
        raise HTTPException(status_code=503, detail="Power BI embed URL is not configured")
    return {"embed_url": POWER_BI_EMBED_URL}


@router.post("/portal/chat")
def chat(payload: ChatRequest, _: Dict[str, Any] = Depends(require_page(PAGE_AI_CHATBOT))):
    from ai.chat_api import process_chat_message

    history = []
    for m in payload.history:
        item: Dict[str, Any] = {"role": m.role, "content": m.content}
        if m.sql:
            item["sql"] = m.sql
        if m.df is not None:
            item["df"] = m.df
        history.append(item)
    try:
        return process_chat_message(payload.message.strip(), history)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Chat request failed. Please try again.",
        ) from exc
