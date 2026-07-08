"""Lazy (on-demand) resolution of expired R001 holds.

There is no persistent background worker in this app. Instead, this
sweep runs at the top of the Analyst Dashboard and Admin Panel (and
optionally the Customer Portal) every time the page loads/reruns. Any
ON_HOLD order whose 180-minute window has elapsed, and that no analyst
has since rejected, is auto-approved.
"""


def sync_expired_holds(conn, cursor) -> int:
    """Auto-approve ON_HOLD orders whose hold window has elapsed.

    Returns the number of orders auto-approved.
    """
    cursor.execute(
        """
        UPDATE master.orders
        SET order_status = 'APPROVED',
            is_fraud = FALSE,
            order_approved_at = NOW()
        WHERE order_status = 'ON_HOLD'
          AND delay_minutes > 0
          AND order_timestamp + (delay_minutes * INTERVAL '1 minute') <= NOW()
          AND order_rejected_at IS NULL
        """
    )
    updated = cursor.rowcount
    conn.commit()
    return updated
