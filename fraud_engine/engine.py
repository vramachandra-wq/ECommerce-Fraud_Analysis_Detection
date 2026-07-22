from typing import Dict, Any, List, Optional
from fraud_engine.rules import RULE_CHECKS
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
# Tier 0: blacklist rules always win regardless of any other rule's configured action.
# Tier 1: iPhone/program rule is next.
# Tier 2 (default): every other rule — resolved amongst themselves as before.
RULE_TIER: Dict[str, int] = {
    "R007": 0,  # Blacklisted IP
    "R011": 0,  # Blacklisted phone
    "R012": 0,  # Blacklisted email
    "R001": 1,  # P2 iPhone 16 rule
}
DEFAULT_RULE_TIER = 2


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

            _RULE_METADATA_CACHE[rule_id] = {
                "action": DB_ACTION_TO_STATUS.get(action_str, "PENDING_REVIEW"),
                "delay_minutes": delay_minutes,
            }
        else:
            _RULE_METADATA_CACHE[rule_id] = {
                "action": "PENDING_REVIEW",
                "delay_minutes": DEFAULT_DELAY_MINUTES,
            }

    return _RULE_METADATA_CACHE[rule_id]


def evaluate_order(cursor: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run all rules against the order context and return the resolved disposition."""
    triggered: List[Dict[str, str]] = []

    for rule_id, check_fn in RULE_CHECKS:
        is_triggered, reason = check_fn(cursor, ctx)
        if is_triggered and reason:
            rule_name = reason.split("—")[0].strip() if "—" in reason else rule_id
            triggered.append({
                "rule_id": rule_id,
                "rule_name": rule_name,
                "rule_description": reason,
            })

    if not triggered:
        return {
            "order_status": "APPROVED",
            "delay_minutes": 0,
            "flagged_reason": None,
            "triggered_rules": [],
            "is_fraud": False,
        }

    final_status = "PENDING_REVIEW"
    delay_minutes = 0

    # Every triggered rule is recorded and contributes to the combined reason,
    # but only the highest-priority TIER decides the final status.
    # Tier 0 (blacklists) beats tier 1 (iPhone rule) beats tier 2 (everything else).
    min_tier = min(_tier_for(rule["rule_id"]) for rule in triggered)
    deciding_rules = [rule for rule in triggered if _tier_for(rule["rule_id"]) == min_tier]

    # Resolve strictness conflict within the deciding tier only
    for rule in deciding_rules:
        meta = _get_rule_metadata(cursor, rule["rule_id"])
        action = meta["action"]

        if STATUS_PRIORITY[action] > STATUS_PRIORITY[final_status]:
            final_status = action

    # Review timeout: MAX delay_minutes across ALL triggered rules so every
    # rule that tagged the order receives its full review window.
    # delay_minutes is always read from rule_master (via _get_rule_metadata).
    for rule in triggered:
        meta = _get_rule_metadata(cursor, rule["rule_id"])
        delay_minutes = max(delay_minutes, int(meta["delay_minutes"] or 0))

    if final_status == "REJECTED":
        delay_minutes = 0
    elif final_status in ("ON_HOLD", "PENDING_REVIEW") and delay_minutes <= 0:
        delay_minutes = DEFAULT_DELAY_MINUTES

    combined_reason = "; ".join(rule["rule_description"] for rule in triggered)
    is_fraud = final_status == "REJECTED"

    return {
        "order_status": final_status,
        "delay_minutes": delay_minutes,
        "flagged_reason": combined_reason,
        "triggered_rules": triggered,
        "is_fraud": is_fraud,
    }


def clear_metadata_cache(rule_id: Optional[str] = None):
    """Clears cached rule metadata."""
    global _RULE_METADATA_CACHE
    if rule_id and rule_id in _RULE_METADATA_CACHE:
        del _RULE_METADATA_CACHE[rule_id]
    else:
        _RULE_METADATA_CACHE.clear()
