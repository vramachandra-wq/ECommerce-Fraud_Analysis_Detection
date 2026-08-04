"""Analyst review action permissions for flagged orders.

All review-queue orders allow Approve, Reject, and Mark as Fraud.
AI recommendations remain advisory only.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

# Kept for compatibility with older call sites / docs.
FULL_REVIEW_RULE_IDS = frozenset({"R001"})


def review_actions_for_rule_ids(rule_ids: Optional[Iterable[str]] = None) -> Dict[str, bool]:
    """Return which analyst decision buttons should be enabled."""
    _ = {str(r).upper() for r in (rule_ids or []) if r}
    return {
        "approve": True,
        "reject": True,
        "mark_fraud": True,
        "full_review": True,
    }


def order_triggered_rule_ids(cursor: Any, order_id: str) -> list[str]:
    cursor.execute(
        """
        SELECT DISTINCT rule_id
        FROM master.order_rule_hits
        WHERE order_id = %s
        ORDER BY rule_id
        """,
        (order_id,),
    )
    return [str(row[0]) for row in cursor.fetchall() if row and row[0]]


def get_review_actions(cursor: Any, order_id: str) -> Dict[str, bool]:
    return review_actions_for_rule_ids(order_triggered_rule_ids(cursor, order_id))


def order_allows_reject_or_fraud(cursor: Any, order_id: str) -> bool:
    """True when Reject / Mark as Fraud are permitted for this order."""
    return bool(get_review_actions(cursor, order_id).get("full_review"))


def filter_orders_allowing_reject(
    cursor: Any, order_ids: Sequence[str]
) -> tuple[list[str], list[str]]:
    """Split order IDs into (allowed_for_reject, blocked)."""
    allowed: list[str] = []
    blocked: list[str] = []
    for oid in order_ids:
        if order_allows_reject_or_fraud(cursor, oid):
            allowed.append(oid)
        else:
            blocked.append(oid)
    return allowed, blocked
