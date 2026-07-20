from typing import Any

def sync_expired_holds(conn: Any, cursor: Any) -> int:
    """
    Auto-approve ON_HOLD orders whose hold window has elapsed.

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
    return updated