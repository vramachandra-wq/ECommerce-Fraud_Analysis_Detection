"""Individual fraud rule checks.

Each check takes (cursor, ctx) where ctx is a dict describing the
in-flight order (not yet inserted) with keys:
    user_id, program_id, product_id, product_name, category,
    quantity, amount, ip_address, device_id, email, address,
    order_timestamp (datetime)

Each check returns (triggered: bool, reason: str | None).
"""

from config import R001_HOLD_MINUTES


def check_r001(cursor, ctx):
    """P2 iPhone 16 Rule: any 'iPhone 16*' product ordered on the P2 track."""
    if ctx["program_id"] == "P2" and "iphone 16" in (ctx["product_name"] or "").lower():
        return True, (
            f"R001: iPhone 16 order on P2 (Premium Electronics) track — "
            f"held for {R001_HOLD_MINUTES}-minute review window"
        )
    return False, None


def check_r002(cursor, ctx):
    """Email Velocity: more than 3 orders from same email within 30 minutes."""
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE email = %s AND order_timestamp >= %s - INTERVAL '30 minutes'
        """,
        (ctx["email"], ctx["order_timestamp"]),
    )
    prior = cursor.fetchone()[0]
    if prior >= 3:  # this order would be the 4th+ => "more than 3"
        return True, f"R002: Email velocity — {prior + 1} orders from {ctx['email']} in last 30 minutes"
    return False, None


def check_r003(cursor, ctx):
    """IP Velocity: more than 5 orders from same IP within 1 hour."""
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE ip_address = %s AND order_timestamp >= %s - INTERVAL '1 hour'
        """,
        (ctx["ip_address"], ctx["order_timestamp"]),
    )
    prior = cursor.fetchone()[0]
    if prior >= 5:
        return True, f"R003: IP velocity — {prior + 1} orders from {ctx['ip_address']} in last hour"
    return False, None


def check_r004(cursor, ctx):
    """Device Velocity: more than 4 orders from same device within 1 hour."""
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE device_id = %s AND order_timestamp >= %s - INTERVAL '1 hour'
        """,
        (ctx["device_id"], ctx["order_timestamp"]),
    )
    prior = cursor.fetchone()[0]
    if prior >= 4:
        return True, f"R004: Device velocity — {prior + 1} orders from device {ctx['device_id']} in last hour"
    return False, None


def check_r005(cursor, ctx):
    """User Spend Velocity: cumulative spend exceeds ₹200,000 within 24 hours."""
    cursor.execute(
        """
        SELECT COALESCE(SUM(amount), 0) FROM master.orders
        WHERE user_id = %s AND order_timestamp >= %s - INTERVAL '24 hours'
        """,
        (ctx["user_id"], ctx["order_timestamp"]),
    )
    prior_spend = float(cursor.fetchone()[0])
    total = prior_spend + float(ctx["amount"])
    if total > 200000:
        return True, f"R005: User spend velocity — ₹{total:,.2f} cumulative in 24 hours exceeds ₹200,000"
    return False, None


def check_r006(cursor, ctx):
    """Multiple Users Same Email: email linked to more than one user_id."""
    cursor.execute(
        """
        SELECT COUNT(DISTINCT user_id) FROM (
            SELECT user_id FROM master.customers WHERE email = %s
            UNION
            SELECT user_id FROM master.orders WHERE email = %s
        ) linked
        """,
        (ctx["email"], ctx["email"]),
    )
    distinct_users = cursor.fetchone()[0]
    if distinct_users > 1:
        return True, f"R006: Email {ctx['email']} is linked to {distinct_users} distinct user IDs"
    return False, None


def check_r007(cursor, ctx):
    """Blacklisted IP: immediate rejection, no analyst review needed."""
    cursor.execute(
        "SELECT reason FROM master.ip_blacklist WHERE ip_address = %s AND is_active = TRUE",
        (ctx["ip_address"],),
    )
    row = cursor.fetchone()
    if row:
        return True, f"R007: IP {ctx['ip_address']} is blacklisted ({row[0]})"
    return False, None


def check_r008(cursor, ctx):
    """Burst Orders: 3 or more orders within 5 minutes from same user."""
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE user_id = %s AND order_timestamp >= %s - INTERVAL '5 minutes'
        """,
        (ctx["user_id"], ctx["order_timestamp"]),
    )
    prior = cursor.fetchone()[0]
    if prior >= 2:  # this order would be the 3rd+ => "three or more"
        return True, f"R008: Burst ordering — {prior + 1} orders from user {ctx['user_id']} within 5 minutes"
    return False, None


def check_r009(cursor, ctx):
    """Address Velocity: more than 5 orders to same address within 24 hours."""
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE address = %s AND order_timestamp >= %s - INTERVAL '24 hours'
        """,
        (ctx["address"], ctx["order_timestamp"]),
    )
    prior = cursor.fetchone()[0]
    if prior >= 5:
        return True, f"R009: Address velocity — {prior + 1} orders to same address in last 24 hours"
    return False, None


def check_r010(cursor, ctx):
    """Device Switching: user uses 2+ distinct devices within a 30-minute window."""
    cursor.execute(
        """
        SELECT COUNT(DISTINCT device_id) FROM master.orders
        WHERE user_id = %s AND order_timestamp >= %s - INTERVAL '30 minutes'
        """,
        (ctx["user_id"], ctx["order_timestamp"]),
    )
    prior_distinct_devices = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT COUNT(*) FROM master.orders
        WHERE user_id = %s AND order_timestamp >= %s - INTERVAL '30 minutes' AND device_id = %s
        """,
        (ctx["user_id"], ctx["order_timestamp"], ctx["device_id"]),
    )
    used_same_device_before = cursor.fetchone()[0] > 0
    total_distinct = prior_distinct_devices + (0 if used_same_device_before else 1)
    if total_distinct >= 2:
        return True, (
            f"R010: Device switching — user {ctx['user_id']} used {total_distinct} "
            f"distinct devices within 30 minutes"
        )
    return False, None


# Ordered rule set. Order matters only for readability/logging; the engine
# resolves conflicts by action severity, not by list order.
RULE_CHECKS = [
    ("R001", check_r001),
    ("R002", check_r002),
    ("R003", check_r003),
    ("R004", check_r004),
    ("R005", check_r005),
    ("R006", check_r006),
    ("R007", check_r007),
    ("R008", check_r008),
    ("R009", check_r009),
    ("R010", check_r010),
]