"""Shared read queries used by more than one portal."""

import pandas as pd


def list_products(cursor):
    cursor.execute(
        "SELECT product_id, product_name, category, price FROM master.products ORDER BY product_name"
    )
    return cursor.fetchall()


def list_programs(cursor):
    cursor.execute("SELECT program_id, program_name FROM master.program_master ORDER BY program_id")
    return cursor.fetchall()


def list_devices(cursor):
    cursor.execute(
        "SELECT device_id, device_name, device_type FROM master.device_master ORDER BY device_id"
    )
    return cursor.fetchall()


def get_queue_orders(cursor):
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


def get_order_detail(cursor, order_id: str):
    cursor.execute("SELECT * FROM master.orders WHERE order_id = %s", (order_id,))
    row = cursor.fetchone()
    if not row:
        return None
    cols = [d.name for d in cursor.description]
    return dict(zip(cols, row))


def get_recent_orders(cursor, limit: int = 100):
    cursor.execute(
        """
        SELECT
            order_id, 
            user_id, 
            customer_name, 
            product_name, 
            quantity,
            amount,
            order_status,
            delay_minutes,
            is_fraud,
            order_timestamp,
            order_approved_at,
            order_rejected_at
        FROM master.orders
        ORDER BY order_timestamp DESC
        LIMIT %s
        """,
        (limit,),
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def get_kpis(cursor):
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


def get_rule_stats(cursor):
    """Counts how often each rule is triggered using the order_rule_hits table."""
    cursor.execute(
        """
        SELECT 
            r.rule_id, 
            r.rule_name, 
            r.action, 
            r.threshold_value, 
            COUNT(h.hit_id) AS times_triggered 
        FROM master.rule_master r
        LEFT JOIN master.order_rule_hits h ON r.rule_id = h.rule_id
        GROUP BY r.rule_id, r.rule_name, r.action, r.threshold_value
        ORDER BY times_triggered DESC, r.rule_id
        """
    )
    cols = [d.name for d in cursor.description]
    return pd.DataFrame(cursor.fetchall(), columns=cols)


def log_order_rule_hits(cur, order_id: str, triggered_rules: list):
    """
    Inserts all triggered rules for a specific order into master.order_rule_hits.
    Cleans the raw reason string to separate the clean rule name and description.
    """
    if not triggered_rules:
        return

    insert_query = """
        INSERT INTO master.order_rule_hits (order_id, rule_id, rule_name, rule_description)
        VALUES (%s, %s, %s, %s)
    """
    
    values = []
    for rule in triggered_rules:
        # 1. Safely extract the rule_id and the raw reason string, regardless of input format
        if isinstance(rule, dict):
            rule_id = rule.get("rule_id", "UNKNOWN")
            raw_reason = rule.get("rule_description", "")
        elif isinstance(rule, tuple) and len(rule) >= 2:
            rule_id = rule[0]
            raw_reason = rule[1]
        elif isinstance(rule, str):
            rule_id = rule
            raw_reason = f"{rule}: Unknown rule — Triggered"
        else:
            continue

        # 2. STRING CLEANING LOGIC
        # Extract the name part (everything before the em-dash "—")
        name_part = raw_reason.split("—")[0].strip() if "—" in raw_reason else raw_reason
        
        # Clean the name (remove the "R002: " prefix)
        clean_name = name_part.split(":", 1)[-1].strip() if ":" in name_part else name_part
        
        # Extract the description part (everything after the em-dash "—")
        clean_desc = raw_reason.split("—", 1)[-1].strip() if "—" in raw_reason else raw_reason

        # 3. Append the perfectly cleaned data
        values.append((order_id, rule_id, clean_name, clean_desc))

    # Execute the bulk insert
    if values:
        try:
            cur.executemany(insert_query, values)
        except Exception as e:
            print(f"DEBUG: Database rejected order_rule_hits insert. Error: {e}")


def get_active_blacklist_entry(cursor, ip_address: str):
    """The currently-active blacklist row for an IP, if any, joined to the analyst name."""
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
    if not row:
        return None
    cols = [d.name for d in cursor.description]
    return dict(zip(cols, row))


def get_orders_over_time(cursor):
    """Daily order counts for the current calendar month (for the Analytics line chart)."""
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


def get_permission_matrix(cursor):
    """Every non-admin analyst with their currently granted page permissions."""
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


def get_analyst_performance(cursor):
    cursor.execute(
        """
        SELECT 
            a.analyst_id, 
            a.employee_name,
            a.role,
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