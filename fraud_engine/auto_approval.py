"""Auto-approval for ON_HOLD orders whose review window has elapsed."""
from typing import Any

# order_timestamp is stored as naive Asia/Kolkata wall-clock time while NOW()
# evaluates in the DB session timezone (often UTC). Convert before comparing.
_HOLD_EXPIRY_SQL = """
    order_timestamp + (delay_minutes * INTERVAL '1 minute')
    <= (NOW() AT TIME ZONE 'Asia/Kolkata')
"""


def sync_expired_holds(conn: Any, cursor: Any) -> int:
    """Auto-approve ON_HOLD orders whose hold window has elapsed.

    Returns the number of orders auto-approved.
    """
    cursor.execute(
        f"""
        UPDATE master.orders
        SET order_status = 'APPROVED',
            is_fraud = FALSE,
            order_approved_at = (NOW() AT TIME ZONE 'Asia/Kolkata')
        WHERE order_status = 'ON_HOLD'
          AND delay_minutes > 0
          AND {_HOLD_EXPIRY_SQL}
          AND order_rejected_at IS NULL
        """
    )
    return cursor.rowcount
