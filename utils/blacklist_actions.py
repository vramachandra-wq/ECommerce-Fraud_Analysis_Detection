"""Blacklist an IP / phone / email by resolving values from an order row."""
from typing import Any, Dict, Tuple

from utils.queries import get_order_detail


def blacklist_entity_from_order(
    cur: Any,
    *,
    order_id: str,
    entity_type: str,
    reason: str,
    blacklisted_by: str,
) -> Tuple[str, str]:
    """Insert/activate blacklist using the order's stored (raw) PII.

    Returns (entity_type, raw_value_used).
    Raises ValueError for not found / missing field / bad entity_type.
    """
    order = get_order_detail(cur, order_id)
    if not order:
        raise ValueError("Order not found")

    entity = (entity_type or "").strip().lower()
    if entity == "ip":
        value = (order.get("ip_address") or "").strip()
        if not value:
            raise ValueError("Order has no IP address")
        # ip_blacklist has no UNIQUE on ip_address (same as /blacklist-ip)
        cur.execute(
            """
            INSERT INTO master.ip_blacklist (ip_address, reason, blacklisted_by)
            VALUES (%s, %s, %s)
            """,
            (value, reason, blacklisted_by),
        )
        return entity, value

    if entity == "phone":
        value = str(order.get("phone_number") or "").strip()
        if not value:
            raise ValueError("Order has no phone number")
        cur.execute(
            """
            INSERT INTO master.phone_blacklist (phone_number, reason, blacklisted_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (phone_number) DO UPDATE SET
                is_active = TRUE,
                reason = EXCLUDED.reason,
                blacklisted_by = EXCLUDED.blacklisted_by,
                blacklisted_at = CURRENT_TIMESTAMP
            """,
            (value, reason, blacklisted_by),
        )
        return entity, value

    if entity == "email":
        value = (order.get("email") or "").strip()
        if not value:
            raise ValueError("Order has no email")
        cur.execute(
            """
            INSERT INTO master.email_blacklist (email, reason, blacklisted_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                is_active = TRUE,
                reason = EXCLUDED.reason,
                blacklisted_by = EXCLUDED.blacklisted_by,
                blacklisted_at = CURRENT_TIMESTAMP
            """,
            (value, reason, blacklisted_by),
        )
        return entity, value

    raise ValueError("Invalid entity type; use ip, phone, or email")
