"""Orchestrates rule evaluation and resolves the final order disposition.

Conflict resolution: when multiple rules trigger with different actions,
the STRICTEST outcome wins (REJECTED > ON_HOLD > PENDING_REVIEW), and all
triggered rules' reasons are combined into a single flagged_reason string.

delay_minutes is set to 180 only when R001 triggers AND the resolved
final status is ON_HOLD. If a stricter rule (e.g. R007 -> REJECTED)
overrides R001's hold, there is no waiting window to honor, so
delay_minutes is 0.
"""

from config import R001_HOLD_MINUTES
from fraud_engine.rules import RULE_CHECKS

RULE_ACTION_MAP = {
    "R001": "ON_HOLD",
    "R002": "PENDING_REVIEW",
    "R003": "PENDING_REVIEW",
    "R004": "PENDING_REVIEW",
    "R005": "PENDING_REVIEW",
    "R006": "PENDING_REVIEW",
    "R007": "REJECTED",
    "R008": "PENDING_REVIEW",
    "R009": "PENDING_REVIEW",
    "R010": "PENDING_REVIEW",
}

STATUS_PRIORITY = {
    "REJECTED": 3,
    "ON_HOLD": 2,
    "PENDING_REVIEW": 1,
    "APPROVED": 0,
}


def evaluate_order(cursor, ctx: dict) -> dict:
    """Run every rule against ctx and return the resolved disposition.

    Returns a dict with keys:
        order_status, delay_minutes, flagged_reason, triggered_rules, is_fraud
    """
    triggered = []
    
    # Collect all triggered rules as dictionaries for the order_rule_hits table
    for rule_id, check_fn in RULE_CHECKS:
        is_triggered, reason = check_fn(cursor, ctx)
        if is_triggered:
            # Extract a short name before the "—" if it exists, else default to rule_id
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

    # Determine the strictest final status
    final_status = "PENDING_REVIEW"
    for rule in triggered:
        action = RULE_ACTION_MAP[rule["rule_id"]]
        if STATUS_PRIORITY[action] > STATUS_PRIORITY[final_status]:
            final_status = action

    # Calculate delays and combined legacy reasons using the dictionary structure
    triggered_ids = [rule["rule_id"] for rule in triggered]
    delay_minutes = R001_HOLD_MINUTES if ("R001" in triggered_ids and final_status == "ON_HOLD") else 0
    combined_reason = "; ".join(rule["rule_description"] for rule in triggered)

    # Only an immediate REJECTED disposition (R007) is fraud at submission
    # time. ON_HOLD / PENDING_REVIEW remain is_fraud=FALSE (schema default)
    # until an analyst (or the 180-min auto-approval sweep) resolves them.
    is_fraud = final_status == "REJECTED"

    return {
        "order_status": final_status,
        "delay_minutes": delay_minutes,
        "flagged_reason": combined_reason,
        "triggered_rules": triggered,  # Now returns the list of dicts required for bulk insert
        "is_fraud": is_fraud,
    }