"""AI / heuristic summaries for orders awaiting analyst review."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai.groq_client import create_chat_completion, get_groq_client
from config import GROQ_SUMMARY_MODEL, is_groq_api_key_configured
from database.order_ai_summary import (
    ensure_order_ai_summaries_table,
    fetch_order_ai_summary,
    upsert_order_ai_summary,
)
from database.order_ai_summary_log import (
    ensure_order_ai_summary_logs_table,
    insert_order_ai_summary_log,
)
from fraud_engine.review_actions import get_review_actions, review_actions_for_rule_ids
from utils.app_logging import get_logger

logger = get_logger("ai.order_review_summary")


def cached_order_ai_summary(cur, order_id: str) -> Optional[Dict[str, Any]]:
    """Return DB-cached summary only — never calls Groq / heuristic generation."""
    ensure_order_ai_summaries_table(cur)
    existing = fetch_order_ai_summary(cur, order_id)
    if not existing or not existing.get("summary_text"):
        return None
    snap = existing.get("context_snapshot")
    return {
        "order_id": order_id,
        "summary": existing["summary_text"],
        "source": existing.get("source") or "cache",
        "model_name": existing.get("model_name"),
        "updated_at": existing.get("updated_at"),
        "cached": True,
        "recommendation": _recommendation_from_snapshot(snap),
        "review_actions": _review_actions_from_snapshot(snap),
    }


def _log_ai_summary(
    cur,
    *,
    order_id: str,
    event: str,
    message: str,
    level: str = "INFO",
    source: Optional[str] = None,
    model_name: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Mirror AI summary lifecycle to file log and master.order_ai_summary_logs."""
    log_fn = logger.warning if level.upper() == "WARNING" else (
        logger.error if level.upper() in {"ERROR", "EXCEPTION"} else logger.info
    )
    log_fn("%s", message)
    insert_order_ai_summary_log(
        cur,
        order_id=order_id,
        event=event,
        message=message,
        level=level,
        source=source,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        details=details,
    )

ORDER_REVIEW_SUMMARY_MAX_TOKENS = 500
ORDER_REVIEW_SUMMARY_REASONING_EFFORT = "low"

ORDER_REVIEW_SUMMARY_SYSTEM = """You are a fraud-operations assistant for Metro Cart e-commerce.
Write a short analyst briefing for ONE order under review.

Rules:
- Use ONLY the supplied JSON context. Do not invent facts.
- 3 to 5 short sentences (or 3–5 bullets). No markdown headings.
- Cover: why the order was flagged, customer history signals, and what an analyst should notice.
- Be neutral and factual. Do not decide approve/reject yourself.
- Never repeat raw full email/phone/IP if masked fields are provided; refer to them generically when needed.
"""


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def gather_order_review_context(cur, order_id: str) -> Optional[Dict[str, Any]]:
    """Pull order + customer history signals used for the AI brief."""
    cur.execute(
        """
        SELECT
            o.order_id, o.user_id, o.customer_name, o.program_id,
            o.product_name, o.category, o.quantity, o.amount,
            o.order_status, o.flagged_reason,
            o.order_timestamp, o.device_id, o.ip_address,
            o.email, o.phone_number, o.city, o.state, o.country
        FROM master.orders o
        WHERE o.order_id = %s
        """,
        (order_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d.name for d in cur.description]
    order = dict(zip(cols, row))

    cur.execute(
        """
        SELECT rule_id, rule_name, rule_description
        FROM master.order_rule_hits
        WHERE order_id = %s
        ORDER BY hit_id
        """,
        (order_id,),
    )
    rules = [
        {"rule_id": r[0], "rule_name": r[1], "rule_description": r[2]}
        for r in cur.fetchall()
    ]

    user_id = order.get("user_id")
    cur.execute(
        """
        SELECT
            COUNT(*)::int AS total_orders,
            COUNT(*) FILTER (WHERE order_status = 'APPROVED')::int AS approved,
            COUNT(*) FILTER (WHERE order_status = 'REJECTED')::int AS rejected,
            COUNT(*) FILTER (WHERE is_fraud = TRUE)::int AS fraud,
            COUNT(*) FILTER (
                WHERE order_status IN ('ON_HOLD', 'PENDING_REVIEW')
            )::int AS in_review,
            COALESCE(ROUND(AVG(amount)::numeric, 2), 0) AS avg_amount,
            COALESCE(ROUND(SUM(amount)::numeric, 2), 0) AS lifetime_spend,
            MIN(order_timestamp) AS first_order_at,
            MAX(order_timestamp) AS last_order_at
        FROM master.orders
        WHERE user_id = %s
        """,
        (user_id,),
    )
    hist_row = cur.fetchone()
    hist_cols = [d.name for d in cur.description]
    history = dict(zip(hist_cols, hist_row)) if hist_row else {}

    cur.execute(
        """
        SELECT order_id, product_name, amount, order_status, is_fraud, order_timestamp
        FROM master.orders
        WHERE user_id = %s AND order_id <> %s
        ORDER BY order_timestamp DESC
        LIMIT 5
        """,
        (user_id, order_id),
    )
    recent_cols = [d.name for d in cur.description]
    recent = [dict(zip(recent_cols, r)) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT created_at, program_id, city, state, country
        FROM master.customers
        WHERE user_id = %s
        """,
        (user_id,),
    )
    cust = cur.fetchone()
    customer = None
    if cust:
        customer = {
            "created_at": cust[0],
            "program_id": cust[1],
            "city": cust[2],
            "state": cust[3],
            "country": cust[4],
        }

    # Shared-signal counts (other customers / other orders).
    email = order.get("email") or ""
    ip = order.get("ip_address") or ""
    device = order.get("device_id") or ""
    phone = order.get("phone_number") or ""

    def _count(sql: str, param: str) -> int:
        if not param:
            return 0
        cur.execute(sql, (param, order_id))
        r = cur.fetchone()
        return int(r[0] or 0) if r else 0

    shared = {
        "other_orders_same_email": _count(
            "SELECT COUNT(*) FROM master.orders WHERE email = %s AND order_id <> %s",
            email,
        ),
        "other_orders_same_ip": _count(
            "SELECT COUNT(*) FROM master.orders WHERE ip_address = %s AND order_id <> %s",
            ip,
        ),
        "other_orders_same_device": _count(
            "SELECT COUNT(*) FROM master.orders WHERE device_id = %s AND order_id <> %s",
            device,
        ),
        "other_users_same_email": 0,
        "other_users_same_phone": 0,
    }
    if email:
        cur.execute(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM master.orders
            WHERE email = %s AND user_id <> %s
            """,
            (email, user_id),
        )
        shared["other_users_same_email"] = int((cur.fetchone() or [0])[0] or 0)
    if phone:
        cur.execute(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM master.orders
            WHERE phone_number = %s AND user_id <> %s
            """,
            (phone, user_id),
        )
        shared["other_users_same_phone"] = int((cur.fetchone() or [0])[0] or 0)

    blacklists = {
        "ip": False,
        "phone": False,
        "email": False,
    }
    if ip:
        cur.execute(
            "SELECT 1 FROM master.ip_blacklist WHERE ip_address = %s AND is_active = TRUE LIMIT 1",
            (ip,),
        )
        blacklists["ip"] = cur.fetchone() is not None
    if phone:
        cur.execute(
            "SELECT 1 FROM master.phone_blacklist WHERE phone_number = %s AND is_active = TRUE LIMIT 1",
            (phone,),
        )
        blacklists["phone"] = cur.fetchone() is not None
    if email:
        cur.execute(
            "SELECT 1 FROM master.email_blacklist WHERE email = %s AND is_active = TRUE LIMIT 1",
            (email,),
        )
        blacklists["email"] = cur.fetchone() is not None

    rule_ids = [r["rule_id"] for r in rules]
    actions = review_actions_for_rule_ids(rule_ids)

    # Mask identifiers in the LLM-facing snapshot (keep structure for analysts).
    safe_order = dict(order)
    if safe_order.get("email"):
        safe_order["email"] = _mask_email(str(safe_order["email"]))
    if safe_order.get("phone_number"):
        safe_order["phone_number"] = _mask_phone(str(safe_order["phone_number"]))
    if safe_order.get("ip_address"):
        safe_order["ip_address"] = _mask_ip(str(safe_order["ip_address"]))

    return _json_safe(
        {
            "order": safe_order,
            "triggered_rules": rules,
            "customer": customer,
            "customer_history": history,
            "recent_orders": recent,
            "shared_signals": shared,
            "blacklists_active": blacklists,
            "review_actions": actions,
        }
    )


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    keep = local[:2] if len(local) >= 2 else local[:1]
    return f"{keep}***@{domain}"


def _mask_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 4:
        return "***"
    return f"{digits[:2]}******{digits[-2:]}"


def _mask_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return "***"


def _heuristic_summary(ctx: Dict[str, Any]) -> str:
    order = ctx.get("order") or {}
    history = ctx.get("customer_history") or {}
    rules = ctx.get("triggered_rules") or []
    shared = ctx.get("shared_signals") or {}

    rule_names = ", ".join(
        f"{r.get('rule_id')} ({r.get('rule_name')})" for r in rules
    ) or (order.get("flagged_reason") or "unknown rule")

    amount = order.get("amount")
    product = order.get("product_name") or "item"
    status = order.get("order_status") or "in review"

    total = int(history.get("total_orders") or 0)
    approved = int(history.get("approved") or 0)
    rejected = int(history.get("rejected") or 0)
    fraud = int(history.get("fraud") or 0)
    avg_amt = history.get("avg_amount") or 0

    bits: List[str] = [
        f"Order {order.get('order_id')} is {status} for {product} "
        f"(฿{amount}) after rule hit(s): {rule_names}."
    ]
    if total <= 1:
        bits.append(
            "This appears to be the customer's first (or only) recorded order on the platform."
        )
    else:
        bits.append(
            f"Customer history: {total} orders — {approved} approved, {rejected} rejected, "
            f"{fraud} marked fraud; lifetime avg ticket ≈ ฿{avg_amt}."
        )

    signals = []
    if int(shared.get("other_users_same_email") or 0) > 0:
        signals.append(
            f"{shared['other_users_same_email']} other user(s) share this email"
        )
    if int(shared.get("other_orders_same_ip") or 0) >= 3:
        signals.append(
            f"{shared['other_orders_same_ip']} other orders from the same IP"
        )
    if int(shared.get("other_orders_same_device") or 0) >= 3:
        signals.append(
            f"{shared['other_orders_same_device']} other orders on the same device"
        )
    if signals:
        bits.append("Linkage signals: " + "; ".join(signals) + ".")

    bits.append(
        "Approve, Reject, and Mark as Fraud are available for this review. "
        "AI action suggestions are advisory only."
    )

    return " ".join(bits)


def _heuristic_recommendation(ctx: Dict[str, Any]) -> Dict[str, str]:
    """Advisory-only action suggestion for the analyst decision panel."""
    history = ctx.get("customer_history") or {}
    shared = ctx.get("shared_signals") or {}
    blacklists = ctx.get("blacklists_active") or {}
    rules = ctx.get("triggered_rules") or []
    rule_ids = {str(r.get("rule_id") or "").upper() for r in rules}

    rejected = int(history.get("rejected") or 0)
    fraud = int(history.get("fraud") or 0)
    total = int(history.get("total_orders") or 0)
    approved = int(history.get("approved") or 0)
    same_email_users = int(shared.get("other_users_same_email") or 0)
    same_ip_orders = int(shared.get("other_orders_same_ip") or 0)
    same_device_orders = int(shared.get("other_orders_same_device") or 0)
    bl_hit = bool(blacklists.get("ip") or blacklists.get("phone") or blacklists.get("email"))

    if bl_hit:
        action = "MARK_FRAUD"
        rationale = (
            "An active blacklist match is present for this order's identifiers; "
            "treat as high risk and consider marking fraud after confirming the hit."
        )
    elif fraud >= 1 or rejected >= 2:
        action = "REJECT"
        rationale = (
            f"Customer history shows elevated risk ({fraud} fraud / {rejected} rejected "
            f"across {total} orders). Rejection is a reasonable next step if the current hit aligns."
        )
    elif same_email_users >= 1 or same_ip_orders >= 5 or same_device_orders >= 5:
        action = "REJECT"
        rationale = (
            "Strong linkage signals (shared email/IP/device across orders) suggest coordinated risk; "
            "reject if the velocity pattern looks abusive."
        )
    elif "R001" in rule_ids:
        action = "INVESTIGATE_FURTHER"
        rationale = (
            "R001 iPhone hold — confirm program eligibility and customer authenticity "
            "before approving; use reject/fraud only if evidence supports it."
        )
    elif total <= 1:
        action = "INVESTIGATE_FURTHER"
        rationale = (
            "Limited customer history (first/only order). Spot-check contact and device "
            "signals before approving."
        )
    elif approved >= max(1, total - 1) and not bl_hit:
        action = "APPROVE"
        rationale = (
            f"Mostly clean history ({approved}/{total} approved) with no active blacklist hit; "
            "approval is reasonable if the current rule explanation looks like a false-positive."
        )
    else:
        action = "APPROVE"
        rationale = (
            "No strong fraud confirmation in the snapshot. Prefer approve if the rule hit looks "
            "borderline, otherwise gather one more corroborating signal first."
        )
    return {"action": action, "rationale": rationale}


def _parse_context_snapshot(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _recommendation_from_snapshot(raw: Any) -> Optional[Dict[str, str]]:
    snap = _parse_context_snapshot(raw)
    if not snap:
        return None
    return _heuristic_recommendation(snap)


def _review_actions_from_snapshot(raw: Any) -> Optional[Dict[str, Any]]:
    snap = _parse_context_snapshot(raw)
    actions = snap.get("review_actions") if snap else None
    return actions if isinstance(actions, dict) else None


def _generate_with_groq(ctx: Dict[str, Any]) -> tuple[str, str, int, int]:
    client = get_groq_client()
    payload = json.dumps(ctx, default=str)
    completion = create_chat_completion(
        client,
        model=GROQ_SUMMARY_MODEL,
        messages=[
            {"role": "system", "content": ORDER_REVIEW_SUMMARY_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Produce the analyst briefing for this order review context:\n"
                    f"{payload}"
                ),
            },
        ],
        max_completion_tokens=ORDER_REVIEW_SUMMARY_MAX_TOKENS,
        temperature=0.2,
        reasoning_effort=ORDER_REVIEW_SUMMARY_REASONING_EFFORT,
    )
    text = (completion.choices[0].message.content or "").strip()
    usage = getattr(completion, "usage", None)
    inp = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
    out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
    if not text:
        raise RuntimeError("empty summary from model")
    return text, GROQ_SUMMARY_MODEL, inp, out


def order_has_rule_hits(cur, order_id: str) -> bool:
    cur.execute(
        "SELECT 1 FROM master.order_rule_hits WHERE order_id = %s LIMIT 1",
        (order_id,),
    )
    return cur.fetchone() is not None


def get_or_create_order_ai_summary(
    cur,
    order_id: str,
    *,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Return cached AI summary for a rule-triggered order, generating when missing.

    Summaries are stored only in master.order_ai_summaries (never on orders).
    Returns None when the order has no rule hits — no summary is created.
    """
    ensure_order_ai_summaries_table(cur)
    ensure_order_ai_summary_logs_table(cur)

    if not order_has_rule_hits(cur, order_id):
        _log_ai_summary(
            cur,
            order_id=order_id,
            event="skipped_no_hits",
            message=f"AI summary skipped for order {order_id} — no fraud rule hits",
        )
        return None

    if not force_refresh:
        existing = fetch_order_ai_summary(cur, order_id)
        if existing and existing.get("summary_text"):
            _log_ai_summary(
                cur,
                order_id=order_id,
                event="cache_hit",
                message=(
                    f"AI summary cache hit for order {order_id} "
                    f"(source={existing.get('source')})"
                ),
                source=existing.get("source"),
                model_name=existing.get("model_name"),
                details={"cached": True},
            )
            return {
                "order_id": order_id,
                "summary": existing["summary_text"],
                "source": existing.get("source") or "cache",
                "model_name": existing.get("model_name"),
                "updated_at": existing.get("updated_at"),
                "cached": True,
                "recommendation": _recommendation_from_snapshot(
                    existing.get("context_snapshot")
                ),
                "review_actions": _review_actions_from_snapshot(
                    existing.get("context_snapshot")
                ),
            }

    ctx = gather_order_review_context(cur, order_id)
    if not ctx:
        _log_ai_summary(
            cur,
            order_id=order_id,
            event="context_missing",
            message=f"AI summary context missing for order {order_id}",
            level="WARNING",
        )
        return {
            "order_id": order_id,
            "summary": "Order not found — unable to generate review summary.",
            "source": "none",
            "model_name": None,
            "updated_at": None,
            "cached": False,
        }

    # Guard: context may load but triggered_rules empty after a race.
    if not (ctx.get("triggered_rules") or []):
        _log_ai_summary(
            cur,
            order_id=order_id,
            event="skipped_no_triggered_rules",
            message=f"AI summary skipped for order {order_id} — context has no triggered rules",
        )
        return None

    source = "heuristic"
    model_name = None
    inp = out = 0
    try:
        if is_groq_api_key_configured():
            text, model_name, inp, out = _generate_with_groq(ctx)
            source = "groq"
        else:
            text = _heuristic_summary(ctx)
            _log_ai_summary(
                cur,
                order_id=order_id,
                event="heuristic_no_key",
                message=(
                    f"AI summary using heuristic for order {order_id} "
                    "(Groq key not configured)"
                ),
                source="heuristic",
            )
    except Exception as exc:
        logger.exception("AI summary Groq failed for order %s: %s", order_id, exc)
        insert_order_ai_summary_log(
            cur,
            order_id=order_id,
            event="groq_failed",
            message=f"AI summary Groq failed for order {order_id}: {exc}",
            level="ERROR",
            source="heuristic_fallback",
            details={"error": str(exc)},
        )
        text = _heuristic_summary(ctx)
        source = "heuristic_fallback"

    upsert_order_ai_summary(
        cur,
        order_id=order_id,
        summary_text=text,
        context_snapshot=ctx,
        model_name=model_name,
        source=source,
        input_tokens=inp,
        output_tokens=out,
    )
    _log_ai_summary(
        cur,
        order_id=order_id,
        event="created",
        message=(
            f"AI summary stored in order_ai_summaries for order {order_id} "
            f"(source={source}, tokens_in={inp}, tokens_out={out})"
        ),
        source=source,
        model_name=model_name,
        input_tokens=inp,
        output_tokens=out,
        details={"force_refresh": force_refresh},
    )

    return {
        "order_id": order_id,
        "summary": text,
        "source": source,
        "model_name": model_name,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "cached": False,
        "recommendation": _heuristic_recommendation(ctx),
        "review_actions": ctx.get("review_actions"),
        "context": {
            "customer_history": ctx.get("customer_history"),
            "triggered_rules": ctx.get("triggered_rules"),
            "shared_signals": ctx.get("shared_signals"),
        },
    }


def attach_review_actions_to_order(cur, order: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Mutate order dict with review_actions based on triggered_rules / DB hits."""
    if not order:
        return order
    triggered = order.get("triggered_rules") or []
    rule_ids = [r.get("rule_id") for r in triggered if isinstance(r, dict)]
    if not rule_ids and order.get("order_id"):
        order["review_actions"] = get_review_actions(cur, str(order["order_id"]))
    else:
        order["review_actions"] = review_actions_for_rule_ids(rule_ids)
    return order
