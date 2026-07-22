"""
Automatic approval of backlog orders whose review window has elapsed.

Uses the shared backlog detection service (fraud_engine.backlog) as the
single source of truth. Do not reimplement timeout checks here.
"""

from typing import Any, List, Optional, Sequence

from fraud_engine.audit import fetch_order_audit_context, log_review_action
from fraud_engine.backlog import lock_backlog_order_ids


SYSTEM_ANALYST_ID = "SYSTEM"
TIMEOUT_COMMENT = "Auto-approved due to review timeout (delay_minutes exceeded)."


def sync_expired_holds(
    conn: Any,
    cursor: Any,
    order_ids: Optional[Sequence[str]] = None,
) -> int:
    """
    Auto-approve backlog orders (ON_HOLD / PENDING_REVIEW) that have
    exceeded their configured delay_minutes from rule_master.

    Optional order_ids limits processing to a subset (still must be backlog).

    Returns the number of orders auto-approved.
    Concurrent runners use FOR UPDATE SKIP LOCKED to avoid double-processing.
    """
    locked_ids: List[str] = lock_backlog_order_ids(cursor, order_ids=order_ids)
    if not locked_ids:
        return 0

    approved = 0
    for order_id in locked_ids:
        ctx = fetch_order_audit_context(cursor, order_id)
        cursor.execute(
            """
            UPDATE master.orders
            SET order_status = 'APPROVED',
                is_fraud = FALSE,
                order_approved_at = NOW(),
                reviewed_by = NULL,
                review_comments = %s
            WHERE order_id = %s
              AND order_status IN ('ON_HOLD', 'PENDING_REVIEW')
            """,
            (TIMEOUT_COMMENT, order_id),
        )
        if cursor.rowcount != 1:
            continue

        log_review_action(
            cursor,
            order_id=order_id,
            action="AUTO_APPROVE",
            reason="Timeout",
            analyst_id=SYSTEM_ANALYST_ID,
            rule_name=ctx.get("rule_name"),
            delay_minutes=ctx.get("delay_minutes"),
            review_comments=TIMEOUT_COMMENT,
        )
        approved += 1

    return approved
