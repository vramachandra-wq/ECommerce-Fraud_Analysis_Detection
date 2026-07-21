"""Shared read queries used by more than one portal."""

import pandas as pd
from typing import Any, List, Dict, Optional

# --- HELPER TO CONVERT CURSOR ROWS TO DICTS ---
def _row_to_dict(cursor: Any, row: Any) -> Dict[str, Any]:
    """Converts a single database row into a dictionary using cursor description."""
    cols = [d.name for d in cursor.description]
    return dict(zip(cols, row))


def list_products(cursor: Any) -> List[tuple]:
    """Lists all available products."""
    cursor.execute(
        "SELECT product_id, product_name, category, price FROM master.products ORDER BY product_name"
    )
    return cursor.fetchall()


def list_programs(cursor: Any) -> List[tuple]:
    """Lists all available programs."""
    cursor.execute("SELECT program_id, program_name FROM master.program_master ORDER BY program_id")
    return cursor.fetchall()


def list_devices(cursor: Any) -> List[tuple]:
    """Lists all available devices."""
    cursor.execute(
        "SELECT device_id, device_name, device_type FROM master.device_master ORDER BY device_id"
    )
    return cursor.fetchall()


def get_queue_orders(cursor: Any) -> pd.DataFrame:
    """Orders awaiting analyst action (ON_HOLD or PENDING_REVIEW)."""
    cursor.execute(
        """
        SELECT order_id, user_id, customer_name, product_name, category, quantity,
               amount, order_status, flagged_reason, order_timestamp, delay_minutes
        FROM master.orders
        WHERE order_status IN ('ON_HOLD', 'PENDING_REVIEW')
        ORDER BY order_timestamp ASC
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_backlog_orders(cursor: Any) -> pd.DataFrame:
    """ON_HOLD or PENDING_REVIEW orders whose delay window has already elapsed.

    order_timestamp is stored as naive local (Asia/Kolkata) wall-clock time
    (see portals/customer_portal.py: datetime.now()), while NOW() evaluates
    in the DB session's timezone (UTC). Comparing them directly causes a
    ~5:30 skew, so NOW() is converted to Asia/Kolkata wall-clock first.
    """
    cursor.execute(
        """
        SELECT order_id, user_id, customer_name, product_name, category, quantity,
               amount, order_status, flagged_reason, order_timestamp, delay_minutes
        FROM master.orders
        WHERE order_status IN ('ON_HOLD', 'PENDING_REVIEW')
          AND delay_minutes > 0
          AND order_timestamp + (delay_minutes * INTERVAL '1 minute') <= (NOW() AT TIME ZONE 'Asia/Kolkata')
        ORDER BY order_timestamp ASC
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_order_detail(cursor: Any, order_id: str) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific order."""
    cursor.execute("SELECT * FROM master.orders WHERE order_id = %s", (order_id,))
    row = cursor.fetchone()
    return _row_to_dict(cursor, row) if row else None


def get_recent_orders(cursor: Any, limit: int = 100) -> pd.DataFrame:
    """Fetches recent orders for the analytics dashboard."""
    cursor.execute(
        """
        SELECT
            order_id, user_id, customer_name, program_id, category, product_name,
            quantity, amount, order_status, delay_minutes, is_fraud,
            flagged_reason, order_timestamp, order_approved_at, order_rejected_at
        FROM master.orders
        ORDER BY order_timestamp DESC
        LIMIT %s
        """,
        (limit,),
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_kpis(cursor: Any) -> Dict[str, Any]:
    """Calculates high-level platform fraud and order metrics."""
    cursor.execute("SELECT COUNT(*) FROM master.orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM master.orders WHERE is_fraud = TRUE")
    total_fraud = cursor.fetchone()[0]
    cursor.execute(
        "SELECT order_status, COUNT(*) FROM master.orders GROUP BY order_status"
    )
    status_counts = dict(cursor.fetchall())
    return {
        "total_orders": total_orders,
        "total_fraud": total_fraud,
        "status_counts": status_counts,
    }


def get_rule_stats(cursor: Any) -> pd.DataFrame:
    """Counts how often each rule is triggered."""
    cursor.execute(
        """
        SELECT 
            r.rule_id, r.rule_name, r.action, r.threshold_value, 
            COUNT(h.hit_id) AS times_triggered 
        FROM master.rule_master r
        LEFT JOIN master.order_rule_hits h ON r.rule_id = h.rule_id
        GROUP BY r.rule_id, r.rule_name, r.action, r.threshold_value
        ORDER BY times_triggered DESC, r.rule_id
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_active_blacklist_entry(cursor: Any, ip_address: str) -> Optional[Dict[str, Any]]:
    """Gets active IP blacklist entry."""
    cursor.execute(
        """
        SELECT b.blacklist_id, b.ip_address, b.reason, b.blacklisted_by,
               a.employee_name AS blacklisted_by_name, b.blacklisted_at
        FROM master.ip_blacklist b
        LEFT JOIN master.analyst_users a ON a.analyst_id = b.blacklisted_by
        WHERE b.ip_address = %s AND b.is_active = TRUE
        """,
        (ip_address,),
    )
    row = cursor.fetchone()
    return _row_to_dict(cursor, row) if row else None


def get_active_phone_blacklist_entry(cursor: Any, phone_number: str) -> Optional[Dict[str, Any]]:
    """Gets active Phone blacklist entry."""
    cursor.execute(
        """
        SELECT b.blacklist_id, b.phone_number, b.reason, b.blacklisted_by,
               a.employee_name AS blacklisted_by_name, b.blacklisted_at
        FROM master.phone_blacklist b
        LEFT JOIN master.analyst_users a ON a.analyst_id = b.blacklisted_by
        WHERE b.phone_number = %s AND b.is_active = TRUE
        """,
        (phone_number,),
    )
    row = cursor.fetchone()
    return _row_to_dict(cursor, row) if row else None


def get_active_email_blacklist_entry(cursor: Any, email: str) -> Optional[Dict[str, Any]]:
    """Gets active Email blacklist entry."""
    cursor.execute(
        """
        SELECT b.blacklist_id, b.email, b.reason, b.blacklisted_by,
               a.employee_name AS blacklisted_by_name, b.blacklisted_at
        FROM master.email_blacklist b
        LEFT JOIN master.analyst_users a ON a.analyst_id = b.blacklisted_by
        WHERE b.email = %s AND b.is_active = TRUE
        """,
        (email,),
    )
    row = cursor.fetchone()
    return _row_to_dict(cursor, row) if row else None


def get_orders_over_time(cursor: Any) -> pd.DataFrame:
    """Daily order counts for the current calendar month."""
    cursor.execute(
        """
        SELECT date_trunc('day', order_timestamp)::date AS order_date, COUNT(*) AS order_count
        FROM master.orders
        WHERE order_timestamp >= date_trunc('month', CURRENT_DATE)
          AND order_timestamp < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
        GROUP BY order_date
        ORDER BY order_date
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_permission_matrix(cursor: Any) -> List[Dict[str, Any]]:
    """Gets all analysts and their granted page permissions."""
    cursor.execute(
        """
        SELECT analyst_id, employee_name, username, role
        FROM master.analyst_users
        WHERE role != 'Admin'
        ORDER BY analyst_id
        """
    )
    cols = [d.name for d in cursor.description]
    analysts = [dict(zip(cols, row)) for row in cursor.fetchall()]

    cursor.execute(
        "SELECT analyst_id, page_key FROM master.analyst_permissions WHERE granted = TRUE"
    )
    granted_by_analyst = {}
    for analyst_id, page_key in cursor.fetchall():
        granted_by_analyst.setdefault(analyst_id, set()).add(page_key)

    for a in analysts:
        a["granted_pages"] = granted_by_analyst.get(a["analyst_id"], set())
    return analysts


def get_analyst_performance(cursor: Any) -> pd.DataFrame:
    """Calculates analyst review statistics."""
    cursor.execute(
        """
        SELECT 
            a.analyst_id, a.employee_name, a.role,
            COUNT(o.order_id) AS orders_reviewed,
            COUNT(o.order_id) FILTER (WHERE o.order_status = 'REJECTED') AS orders_rejected
        FROM master.analyst_users a
        LEFT JOIN master.orders o ON o.reviewed_by = a.analyst_id
        GROUP BY a.analyst_id, a.employee_name, a.role
        ORDER BY a.analyst_id
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)