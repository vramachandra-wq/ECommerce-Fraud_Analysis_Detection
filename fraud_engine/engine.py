from typing import Dict, Any, List, Optional
from fraud_engine.rules import RULE_CHECKS

STATUS_PRIORITY: Dict[str, int] = {
    "REJECTED": 3,
    "ON_HOLD": 2,
    "PENDING_REVIEW": 1,
    "APPROVED": 0,
}

# Maps database ENUM/VARCHAR actions to internal application statuses[cite: 7]
DB_ACTION_TO_STATUS: Dict[str, str] = {
    "REJECTED": "REJECTED",
    "HOLD": "ON_HOLD",
    "REVIEW": "PENDING_REVIEW",
    "PASS": "APPROVED",  
    "APPROVE": "APPROVED"   
}

# In-memory cache to minimize database hits[cite: 7]
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
    """Fetches rule actions and intervals directly from the master.rule_master table[cite: 7]."""
    if rule_id not in _RULE_METADATA_CACHE:
        cursor.execute(
            """
            SELECT action, time_interval_value, time_interval_unit 
            FROM master.rule_master 
            WHERE rule_id = %s
            """,
            (rule_id,)
        )
        row = cursor.fetchone()
        
        if row:
            action_str = row[0].upper() if row[0] else "REVIEW"
            interval_val = row[1] or 0
            interval_unit = (row[2] or "MINUTE").upper()
            
            # Convert everything to minutes[cite: 7]
            if interval_unit == "HOUR":
                delay_minutes = interval_val * 60
            elif interval_unit == "DAY":
                delay_minutes = interval_val * 1440
            else:
                delay_minutes = interval_val # Defaults to MINUTE
                
            _RULE_METADATA_CACHE[rule_id] = {
                "action": DB_ACTION_TO_STATUS.get(action_str, "PENDING_REVIEW"),
                "delay_minutes": delay_minutes
            }
        else:
            _RULE_METADATA_CACHE[rule_id] = {"action": "PENDING_REVIEW", "delay_minutes": 0}
            
    return _RULE_METADATA_CACHE[rule_id]


def evaluate_order(cursor: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run all rules against the order context and return the resolved disposition[cite: 7]."""
    triggered: List[Dict[str, str]] = []
    
    for rule_id, check_fn in RULE_CHECKS:
        is_triggered, reason = check_fn(cursor, ctx)
        if is_triggered and reason:
            # Shorten name if possible[cite: 7]
            rule_name = reason.split("—")[0].strip() if "—" in reason else rule_id
            triggered.append({
                "rule_id": rule_id,
                "rule_name": rule_name,
                "rule_description": reason
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
    # but only the highest-priority TIER decides the final status/delay.
    # Tier 0 (blacklists) beats tier 1 (iPhone rule) beats tier 2 (everything else).
    min_tier = min(_tier_for(rule["rule_id"]) for rule in triggered)
    deciding_rules = [rule for rule in triggered if _tier_for(rule["rule_id"]) == min_tier]

    # Resolve strictness conflict within the deciding tier only[cite: 7]
    for rule in deciding_rules:
        meta = _get_rule_metadata(cursor, rule["rule_id"])
        action = meta["action"]

        if STATUS_PRIORITY[action] > STATUS_PRIORITY[final_status]:
            final_status = action

        if action == "ON_HOLD":
            delay_minutes = max(delay_minutes, meta["delay_minutes"])

    # Discard delay if stricter outcome found[cite: 7]
    if final_status == "REJECTED":
        delay_minutes = 0

    # Combined reason includes ALL triggered rules (order passes through every rule),
    # even though only the top-priority tier drives the status decision.
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
    """Clears cached rule metadata[cite: 7]."""
    global _RULE_METADATA_CACHE
    if rule_id and rule_id in _RULE_METADATA_CACHE:
        del _RULE_METADATA_CACHE[rule_id]
    else:
        _RULE_METADATA_CACHE.clear()