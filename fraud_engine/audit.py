"""Append-only audit logging for order review actions."""

from typing import Any, Optional


def log_review_action(
    cursor: Any,
    *,
    order_id: str,
    action: str,
    reason: str = "Manual",
    analyst_id: Optional[str] = None,
    rule_name: Optional[str] = None,
    delay_minutes: Optional[int] = None,
    review_comments: Optional[str] = None,
) -> None:
    """
    Record an approve / reject / mark-as-fraud / auto-approval event.

    reason: 'Manual' for analyst actions, 'Timeout' for scheduler auto-approval.
    """
    cursor.execute(
        """
        INSERT INTO master.order_review_audit
            (order_id, analyst_id, action, rule_name, delay_minutes, reason, review_comments)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            order_id,
            analyst_id,
            action,
            rule_name,
            delay_minutes,
            reason,
            review_comments,
        ),
    )


def fetch_order_audit_context(cursor: Any, order_id: str) -> dict:
    """Rule names + applicable delay for audit rows."""
    from fraud_engine.backlog import get_applicable_delay_minutes

    delay = get_applicable_delay_minutes(cursor, order_id)
    cursor.execute(
        """
        SELECT STRING_AGG(DISTINCT rule_name, ', ' ORDER BY rule_name)
        FROM master.order_rule_hits
        WHERE order_id = %s
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    rule_name = row[0] if row and row[0] else None
    return {"rule_name": rule_name, "delay_minutes": delay}
