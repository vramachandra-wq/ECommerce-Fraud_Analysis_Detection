"""Portal API for the React analyst frontend."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import authenticate_credentials, get_current_session, require_page
from auth.analyst_auth import (
    ALL_PAGES,
    PAGE_ADMIN_PANEL,
    PAGE_AI_CHATBOT,
    PAGE_FRAUD_DASHBOARD,
    PAGE_LABELS,
    PAGE_POWER_BI,
)
from config import DB_CONFIG, POWER_BI_EMBED_URL
from database.connection import get_cursor
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
    get_kpis,
    get_order_detail,
    get_orders_over_time,
    get_permission_matrix,
    get_recent_orders,
    get_rule_stats,
)

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
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
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


class ChatMessage(BaseModel):
    role: str
    content: str
    # Kept client-side for follow-up context; never shown in the portal UI.
    sql: str | None = None
    df: List[Dict[str, Any]] | None = None


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


@router.post("/auth/login")
def login(payload: LoginRequest):
    session = authenticate_credentials(payload.username.strip(), payload.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return session


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
    }


@router.post("/portal/sync-holds")
def sync_holds(_: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    with get_cursor(commit=True) as (conn, cur):
        count = sync_expired_holds(conn, cur)
    return {"auto_approved": count}


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


@router.get("/portal/backlog")
def backlog(_: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    """Overdue ON_HOLD / PENDING_REVIEW orders (past delay_minutes window)."""
    with get_cursor() as (_, cur):
        df = detect_backlog_orders(cur)
        stats = get_backlog_stats(cur)
    return {"orders": _df_records(df), "stats": _jsonable_dict(stats)}


@router.get("/portal/orders/{order_id}")
def order_detail(order_id: str, _: Dict[str, Any] = Depends(require_page(PAGE_FRAUD_DASHBOARD))):
    with get_cursor() as (_, cur):
        order = get_order_detail(cur, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        ip_bl = get_active_blacklist_entry(cur, order["ip_address"])
        phone_bl = get_active_phone_blacklist_entry(cur, order.get("phone_number") or "")
        email_bl = get_active_email_blacklist_entry(cur, order.get("email") or "")
        timing = _order_timing(cur, order)
    return {
        "order": _jsonable_dict(order),
        "timing": _jsonable_dict(timing),
        "blacklists": {
            "ip": _jsonable_dict(ip_bl) if ip_bl else None,
            "phone": _jsonable_dict(phone_bl) if phone_bl else None,
            "email": _jsonable_dict(email_bl) if email_bl else None,
        },
    }


@router.get("/portal/blacklist/{entity_type}/{value}")
def blacklist_lookup(
    entity_type: str,
    value: str,
    _: Dict[str, Any] = Depends(require_page(PAGE_ADMIN_PANEL)),
):
    with get_cursor() as (_, cur):
        if entity_type == "ip":
            entry = get_active_blacklist_entry(cur, value)
        elif entity_type == "phone":
            entry = get_active_phone_blacklist_entry(cur, value)
        elif entity_type == "email":
            entry = get_active_email_blacklist_entry(cur, value)
        else:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    return {"entry": _jsonable_dict(entry) if entry else None}


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
        raise HTTPException(status_code=500, detail=str(exc)) from exc
