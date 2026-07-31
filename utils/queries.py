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


def get_order_detail(cursor: Any, order_id: str) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific order, including line items when present."""
    from database.order_items import enrich_order_with_items

    cursor.execute("SELECT * FROM master.orders WHERE order_id = %s", (order_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return enrich_order_with_items(cursor, _row_to_dict(cursor, row))


def get_recent_orders(cursor: Any, limit: int = 100) -> pd.DataFrame:
    """Fetches recent orders for admin analytics / latest-orders panels."""
    cursor.execute(
        """
        SELECT
            o.order_id, o.user_id, o.customer_name, o.product_name, o.quantity,
            o.amount, o.order_status, o.delay_minutes, o.is_fraud,
            o.order_timestamp, o.order_approved_at, o.order_rejected_at,
            COALESCE(
                (
                    SELECT COUNT(*)::int
                    FROM master.order_items oi
                    WHERE oi.order_id = o.order_id
                ),
                0
            ) AS item_count
        FROM master.orders o
        ORDER BY o.order_timestamp DESC
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


def get_dashboard_order_trend(cursor: Any, period: str = "month") -> Dict[str, Any]:
    """
    Order volume by status for dashboard Statistics chart.

    period:
      - today  → hourly buckets for the current calendar day
      - week   → daily buckets for the current ISO week (Mon–Sun)
      - month  → daily buckets for the current calendar month
    """
    period = (period or "month").lower().strip()
    if period not in {"today", "week", "month"}:
        period = "month"

    if period == "today":
        granularity = "hour"
        start_sql = "date_trunc('day', CURRENT_TIMESTAMP)"
        end_sql = "date_trunc('day', CURRENT_TIMESTAMP) + INTERVAL '1 day'"
        step_sql = "INTERVAL '1 hour'"
    elif period == "week":
        granularity = "day"
        # PostgreSQL date_trunc('week') starts Monday.
        start_sql = "date_trunc('week', CURRENT_DATE)"
        end_sql = "date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'"
        step_sql = "INTERVAL '1 day'"
    else:
        granularity = "day"
        start_sql = "date_trunc('month', CURRENT_DATE)"
        end_sql = "date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'"
        step_sql = "INTERVAL '1 day'"

    cursor.execute(
        f"""
        WITH bounds AS (
            SELECT {start_sql} AS start_ts, {end_sql} AS end_ts
        ),
        buckets AS (
            SELECT generate_series(
                (SELECT start_ts FROM bounds),
                (SELECT end_ts FROM bounds) - {step_sql},
                {step_sql}
            ) AS bucket_ts
        ),
        agg AS (
            SELECT
                date_trunc('{granularity}', o.order_timestamp) AS bucket_ts,
                COUNT(*)::int AS orders,
                COUNT(*) FILTER (
                    WHERE o.order_status IN ('PENDING_REVIEW', 'ON_HOLD')
                )::int AS in_review,
                COUNT(*) FILTER (
                    WHERE o.order_status = 'APPROVED'
                )::int AS approved,
                COUNT(*) FILTER (
                    WHERE o.order_status = 'REJECTED' OR o.is_fraud IS TRUE
                )::int AS rejected
            FROM master.orders o
            CROSS JOIN bounds b
            WHERE o.order_timestamp >= b.start_ts
              AND o.order_timestamp < b.end_ts
            GROUP BY 1
        )
        SELECT
            b.bucket_ts,
            COALESCE(a.orders, 0) AS orders,
            COALESCE(a.in_review, 0) AS in_review,
            COALESCE(a.approved, 0) AS approved,
            COALESCE(a.rejected, 0) AS rejected
        FROM buckets b
        LEFT JOIN agg a ON a.bucket_ts = b.bucket_ts
        ORDER BY b.bucket_ts
        """
    )
    cols = [d.name for d in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

    points: List[Dict[str, Any]] = []
    totals = {"orders": 0, "in_review": 0, "approved": 0, "rejected": 0}
    for row in rows:
        ts = row["bucket_ts"]
        if hasattr(ts, "strftime"):
            if granularity == "hour":
                key = ts.strftime("%Y-%m-%dT%H:00:00")
                label = ts.strftime("%H:%M")
            else:
                key = ts.strftime("%Y-%m-%d")
                label = ts.strftime("%a %d") if period == "week" else ts.strftime("%d %b")
        else:
            key = str(ts)
            label = str(ts)

        point = {
            "key": key,
            "label": label,
            "orders": int(row["orders"] or 0),
            "in_review": int(row["in_review"] or 0),
            "approved": int(row["approved"] or 0),
            "rejected": int(row["rejected"] or 0),
        }
        points.append(point)
        for metric in totals:
            totals[metric] += point[metric]

    return {
        "period": period,
        "granularity": granularity,
        "totals": totals,
        "points": points,
    }


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


def get_all_rules(cursor: Any) -> List[Dict[str, Any]]:
    """All fraud rules from rule_master (for portal rule configuration)."""
    cursor.execute(
        """
        SELECT rule_id, rule_name, rule_description, rule_type,
               action, threshold_value, time_interval_value, time_interval_unit,
               delay_minutes
        FROM master.rule_master
        ORDER BY rule_id
        """
    )
    cols = [d.name for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def get_review_audit_log(
    cursor: Any,
    *,
    limit: int = 100,
    offset: int = 0,
    order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Paginated order review audit trail with analyst and order context."""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    filters = ""
    params: List[Any] = []
    if order_id:
        filters = "WHERE a.order_id = %s"
        params.append(order_id.strip())

    cursor.execute(
        f"""
        SELECT COUNT(*) FROM master.order_review_audit a {filters}
        """,
        params,
    )
    total = int(cursor.fetchone()[0])

    cursor.execute(
        f"""
        SELECT
            a.audit_id,
            a.order_id,
            a.analyst_id,
            au.employee_name AS analyst_name,
            a.action,
            a.rule_name,
            a.delay_minutes,
            a.reason,
            a.review_comments,
            a.created_at,
            o.customer_name,
            o.order_status
        FROM master.order_review_audit a
        LEFT JOIN master.analyst_users au ON au.analyst_id = a.analyst_id
        LEFT JOIN master.orders o ON o.order_id = a.order_id
        {filters}
        ORDER BY a.created_at DESC, a.audit_id DESC
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    )
    cols = [d.name for d in cursor.description]
    entries = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}