"""Which analyst review actions are allowed for an order / rule set."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def review_actions_for_rule_ids(rule_ids: Iterable[Any] = ()) -> Dict[str, bool]:
    """
    All flagged review-queue orders allow Approve, Reject, and Mark as Fraud.
    rule_ids is accepted for call-site compatibility but does not gate actions.
    """
    _ = {str(r or "").strip().upper() for r in (rule_ids or [])}
    return {
        "approve": True,
        "reject": True,
        "mark_fraud": True,
        "full_review": True,
    }


def get_review_actions(cur, order_id: str) -> Dict[str, bool]:
    cur.execute(
        """
        SELECT rule_id
        FROM master.order_rule_hits
        WHERE order_id = %s
        """,
        (order_id,),
    )
    rule_ids: List[str] = [str(r[0]) for r in cur.fetchall()]
    return review_actions_for_rule_ids(rule_ids)
