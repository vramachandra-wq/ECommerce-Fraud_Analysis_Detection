from typing import Dict, Any, List, Optional, Iterable, Set

from fraud_engine.rules import (
    PRODUCT_SCOPED_RULE_IDS,
    R001_HOLD_DELAY_MINUTES,
    RULE_CHECKS,
)
from fraud_engine.backlog import DEFAULT_DELAY_MINUTES

STATUS_PRIORITY: Dict[str, int] = {
    "REJECTED": 3,
    "ON_HOLD": 2,
    "PENDING_REVIEW": 1,
    "APPROVED": 0,
}

# Maps database ENUM/VARCHAR actions to internal application statuses
DB_ACTION_TO_STATUS: Dict[str, str] = {
    "REJECTED": "REJECTED",
    "HOLD": "ON_HOLD",
    "REVIEW": "PENDING_REVIEW",
    "PASS": "APPROVED",
    "APPROVE": "APPROVED",
}

# In-memory cache to minimize database hits
_RULE_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}

# Priority tiers for conflict resolution. Lower number = decided first.
# Tier 0: blacklist rules win among non-R001 hits.
# Tier 1 (default): every other rule — resolved amongst themselves as before.
# R001 (P2 + iPhone) is handled as a hard override in resolve_disposition:
# when it triggers, status is always ON_HOLD for 180 minutes regardless of
# other flagged rules (blacklists included). Those other hits are still recorded.
RULE_TIER: Dict[str, int] = {
    "R007": 0,  # Blacklisted IP
    "R011": 0,  # Blacklisted phone
    "R012": 0,  # Blacklisted email
}
DEFAULT_RULE_TIER = 1
R001_RULE_ID = "R001"


def _tier_for(rule_id: str) -> int:
    return RULE_TIER.get(rule_id, DEFAULT_RULE_TIER)


def _get_rule_metadata(cursor: Any, rule_id: str) -> Dict[str, Any]:
    """
    Fetches rule action and delay_minutes from master.rule_master.

    delay_minutes is the sole source of truth for review timeout — never
    derive it from time_interval_* (those remain for velocity windows only).
    """
    if rule_id not in _RULE_METADATA_CACHE:
        cursor.execute(
            """
            SELECT action, delay_minutes
            FROM master.rule_master
            WHERE rule_id = %s
            """,
            (rule_id,),
        )
        row = cursor.fetchone()

        if row:
            action_str = row[0].upper() if row[0] else "REVIEW"
            delay_minutes = int(row[1]) if row[1] is not None else DEFAULT_DELAY_MINUTES
            if delay_minutes <= 0:
                delay_minutes = DEFAULT_DELAY_MINUTES
            # Product rule R001 always uses a 180-minute HOLD window.
            if rule_id == "R001":
                action_str = "HOLD"
                delay_minutes = R001_HOLD_DELAY_MINUTES

            _RULE_METADATA_CACHE[rule_id] = {
                "action": DB_ACTION_TO_STATUS.get(action_str, "PENDING_REVIEW"),
                "delay_minutes": delay_minutes,
            }
        else:
            _RULE_METADATA_CACHE[rule_id] = {
                "action": "PENDING_REVIEW" if rule_id != "R001" else "ON_HOLD",
                "delay_minutes": (
                    R001_HOLD_DELAY_MINUTES if rule_id == "R001" else DEFAULT_DELAY_MINUTES
                ),
            }

    return _RULE_METADATA_CACHE[rule_id]


def _collect_triggered_rules(
    cursor: Any,
    ctx: Dict[str, Any],
    *,
    only_rule_ids: Optional[Set[str]] = None,
    exclude_rule_ids: Optional[Set[str]] = None,
) -> List[Dict[str, str]]:
    """Run selected rule checks and return triggered rule hit dicts."""
    triggered: List[Dict[str, str]] = []
    for rule_id, check_fn in RULE_CHECKS:
        if only_rule_ids is not None and rule_id not in only_rule_ids:
            continue
        if exclude_rule_ids is not None and rule_id in exclude_rule_ids:
            continue
        is_triggered, reason = check_fn(cursor, ctx)
        if is_triggered and reason:
            rule_name = reason.split("—")[0].strip() if "—" in reason else rule_id
            triggered.append(
                {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "rule_description": reason,
                }
            )
    return triggered


def resolve_disposition(cursor: Any, triggered: List[Dict[str, str]]) -> Dict[str, Any]:
    """Roll triggered rule hits into a single order disposition."""
    if not triggered:
        return {
            "order_status": "APPROVED",
            "delay_minutes": 0,
            "flagged_reason": None,
            "triggered_rules": [],
            "is_fraud": False,
        }

    combined_reason = "; ".join(rule["rule_description"] for rule in triggered)
    r001_hit = any(rule["rule_id"] == R001_RULE_ID for rule in triggered)

    # P2 iPhone (R001): always ON_HOLD for 180 minutes, no matter which other
    # rules also flagged. Other hits remain in flagged_reason / triggered_rules.
    if r001_hit:
        _get_rule_metadata(cursor, R001_RULE_ID)  # warm cache / enforce HOLD meta
        return {
            "order_status": "ON_HOLD",
            "delay_minutes": R001_HOLD_DELAY_MINUTES,
            "flagged_reason": combined_reason,
            "triggered_rules": triggered,
            "is_fraud": False,
        }

    final_status = "APPROVED"

    # Every triggered rule is recorded and contributes to the combined reason,
    # but only the highest-priority TIER decides the final status.
    # Tier 0 (blacklists) beats tier 1 (everything else).
    min_tier = min(_tier_for(rule["rule_id"]) for rule in triggered)
    deciding_rules = [rule for rule in triggered if _tier_for(rule["rule_id"]) == min_tier]

    # Resolve strictness conflict within the deciding tier only
    for rule in deciding_rules:
        meta = _get_rule_metadata(cursor, rule["rule_id"])
        action = meta["action"]

        if STATUS_PRIORITY[action] > STATUS_PRIORITY[final_status]:
            final_status = action

    # Non-R001: orders.delay_minutes stays 0; backlog/scheduler uses the fixed
    # DEFAULT_DELAY_MINUTES window from order_timestamp.
    delay_minutes = 0
    is_fraud = final_status == "REJECTED"

    return {
        "order_status": final_status,
        "delay_minutes": delay_minutes,
        "flagged_reason": combined_reason,
        "triggered_rules": triggered,
        "is_fraud": is_fraud,
    }


def evaluate_order(cursor: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run all rules against a single-product order context (legacy / tests)."""
    triggered = _collect_triggered_rules(cursor, ctx)
    return resolve_disposition(cursor, triggered)


def evaluate_order_with_items(
    cursor: Any,
    base_ctx: Dict[str, Any],
    lines: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate a multi-item checkout.

    - Product-scoped rules (e.g. R001 P2 iPhone) run **per line item**.
    - Order-scoped rules (velocity, blacklist, …) run **once** on basket totals.
    - Hits are merged and rolled up to one order status / flagged_reason.
    """
    line_list = [dict(line) for line in (lines or [])]
    if not line_list:
        return evaluate_order(cursor, base_ctx)

    total_amount = round(sum(float(line.get("line_amount") or 0) for line in line_list), 2)
    total_qty = sum(int(line.get("quantity") or 0) for line in line_list)
    first = line_list[0]

    order_ctx = {
        **base_ctx,
        "product_id": first.get("product_id") or base_ctx.get("product_id"),
        "product_name": first.get("product_name") or base_ctx.get("product_name"),
        "category": first.get("category") or base_ctx.get("category"),
        "quantity": total_qty or base_ctx.get("quantity") or 1,
        "amount": total_amount if total_amount else base_ctx.get("amount"),
    }

    triggered: List[Dict[str, str]] = _collect_triggered_rules(
        cursor,
        order_ctx,
        exclude_rule_ids=set(PRODUCT_SCOPED_RULE_IDS),
    )

    item_results: List[Dict[str, Any]] = []
    for line in line_list:
        line_ctx = {
            **base_ctx,
            "product_id": line.get("product_id"),
            "product_name": line.get("product_name"),
            "category": line.get("category"),
            "quantity": int(line.get("quantity") or 1),
            "amount": float(line.get("line_amount") or 0),
        }
        line_hits = _collect_triggered_rules(
            cursor,
            line_ctx,
            only_rule_ids=set(PRODUCT_SCOPED_RULE_IDS),
        )
        annotated: List[Dict[str, str]] = []
        for hit in line_hits:
            product_label = line.get("product_name") or line.get("product_id") or "item"
            annotated.append(
                {
                    **hit,
                    "product_id": str(line.get("product_id") or ""),
                    "product_name": str(line.get("product_name") or ""),
                    "rule_description": f"[{product_label}] {hit['rule_description']}",
                }
            )
            triggered.append(annotated[-1])

        line_disposition = resolve_disposition(cursor, line_hits)
        item_results.append(
            {
                "product_id": line.get("product_id"),
                "product_name": line.get("product_name"),
                "quantity": int(line.get("quantity") or 1),
                "line_amount": float(line.get("line_amount") or 0),
                "order_status": line_disposition["order_status"],
                "flagged_reason": line_disposition["flagged_reason"],
                "triggered_rules": annotated,
            }
        )

    disposition = resolve_disposition(cursor, triggered)
    disposition["item_results"] = item_results
    return disposition


def clear_metadata_cache(rule_id: Optional[str] = None):
    """Clears cached rule metadata."""
    global _RULE_METADATA_CACHE
    if rule_id and rule_id in _RULE_METADATA_CACHE:
        del _RULE_METADATA_CACHE[rule_id]
    else:
        _RULE_METADATA_CACHE.clear()
