from typing import Dict, Any, Tuple, Optional, Callable, List

# In-memory caches to prevent querying master.rule_master repeatedly 
_INTERVAL_CACHE: Dict[str, str] = {}
_THRESHOLD_CACHE: Dict[str, float] = {}

def _get_interval(cursor: Any, rule_id: str) -> str:
    """Fetches and caches the time interval from master.rule_master."""
    if rule_id not in _INTERVAL_CACHE:
        cursor.execute(
            "SELECT time_interval_value, time_interval_unit FROM master.rule_master WHERE rule_id = %s",
            (rule_id,)
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            _INTERVAL_CACHE[rule_id] = f"{row[0]} {row[1]}"
        else:
            _INTERVAL_CACHE[rule_id] = "0 MINUTE"
            
    return _INTERVAL_CACHE[rule_id]

def _get_threshold(cursor: Any, rule_id: str, fallback_value: float) -> float:
    """Fetches and caches the threshold value from master.rule_master."""
    if rule_id not in _THRESHOLD_CACHE:
        cursor.execute(
            "SELECT threshold_value FROM master.rule_master WHERE rule_id = %s",
            (rule_id,)
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            _THRESHOLD_CACHE[rule_id] = float(row[0])
        else:
            _THRESHOLD_CACHE[rule_id] = float(fallback_value)
            
    return _THRESHOLD_CACHE[rule_id]


def check_r001(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """P2 iPhone 16 Rule."""
    if ctx["program_id"] == "P2" and "iphone 16" in (ctx.get("product_name") or "").lower():
        interval_str = _get_interval(cursor, "R001")
        return True, f"R001: iPhone 16 order on P2 track — held for {interval_str} review window"
    return False, None


def check_r002(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Email Velocity."""
    interval = _get_interval(cursor, "R002")
    threshold = _get_threshold(cursor, "R002", 3.0)
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE email = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["email"], ctx["order_timestamp"], interval),
    )
    prior = cursor.fetchone()[0]
    if prior >= threshold: 
        return True, f"R002: Email velocity — {prior + 1} orders from {ctx['email']} in last {interval}"
    return False, None


def check_r003(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """IP Velocity."""
    interval = _get_interval(cursor, "R003")
    threshold = _get_threshold(cursor, "R003", 5.0)
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE ip_address = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["ip_address"], ctx["order_timestamp"], interval),
    )
    prior = cursor.fetchone()[0]
    if prior >= threshold:
        return True, f"R003: IP velocity — {prior + 1} orders from {ctx['ip_address']} in last {interval}"
    return False, None


def check_r004(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Device Velocity."""
    interval = _get_interval(cursor, "R004")
    threshold = _get_threshold(cursor, "R004", 4.0)
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE device_id = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["device_id"], ctx["order_timestamp"], interval),
    )
    prior = cursor.fetchone()[0]
    if prior >= threshold:
        return True, f"R004: Device velocity — {prior + 1} orders from device {ctx['device_id']} in last {interval}"
    return False, None


def check_r005(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """User Spend Velocity."""
    interval = _get_interval(cursor, "R005")
    threshold = _get_threshold(cursor, "R005", 200000.0)
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM master.orders WHERE user_id = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["user_id"], ctx["order_timestamp"], interval),
    )
    prior_spend = float(cursor.fetchone()[0])
    total = prior_spend + float(ctx["amount"])
    if total > threshold:
        return True, f"R005: User spend velocity — ₹{total:,.2f} cumulative in last {interval} exceeds ₹{threshold:,.2f}"
    return False, None


def check_r006(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Multiple Users Same Email."""
    threshold = _get_threshold(cursor, "R006", 1.0)
    cursor.execute(
        """SELECT COUNT(DISTINCT user_id) FROM (
            SELECT user_id FROM master.customers WHERE email = %s
            UNION
            SELECT user_id FROM master.orders WHERE email = %s
        ) linked""",
        (ctx["email"], ctx["email"]),
    )
    distinct_users = cursor.fetchone()[0]
    if distinct_users > threshold:
        return True, f"R006: Email {ctx['email']} is linked to {distinct_users} distinct user IDs"
    return False, None


def check_r007(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Blacklisted IP."""
    cursor.execute("SELECT reason FROM master.ip_blacklist WHERE ip_address = %s AND is_active = TRUE", (ctx["ip_address"],))
    row = cursor.fetchone()
    if row:
        return True, f"R007: IP {ctx['ip_address']} is blacklisted ({row[0]})"
    return False, None


def check_r008(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Burst Orders."""
    interval = _get_interval(cursor, "R008")
    threshold = _get_threshold(cursor, "R008", 3.0)
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE user_id = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["user_id"], ctx["order_timestamp"], interval),
    )
    prior = cursor.fetchone()[0]
    if prior + 1 >= threshold:
        return True, f"R008: Burst ordering — {prior + 1} orders from user {ctx['user_id']} within {interval}"
    return False, None


def check_r009(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Address Velocity."""
    interval = _get_interval(cursor, "R009")
    threshold = _get_threshold(cursor, "R009", 5.0)
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE address = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["address"], ctx["order_timestamp"], interval),
    )
    prior = cursor.fetchone()[0]
    if prior >= threshold:
        return True, f"R009: Address velocity — {prior + 1} orders to same address in last {interval}"
    return False, None


def check_r010(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Device Switching."""
    interval = _get_interval(cursor, "R010")
    threshold = _get_threshold(cursor, "R010", 2.0)
    cursor.execute(
        "SELECT COUNT(DISTINCT device_id) FROM master.orders WHERE user_id = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL)",
        (ctx["user_id"], ctx["order_timestamp"], interval),
    )
    prior_distinct = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM master.orders WHERE user_id = %s AND order_timestamp >= %s - CAST(%s AS INTERVAL) AND device_id = %s",
        (ctx["user_id"], ctx["order_timestamp"], interval, ctx["device_id"]),
    )
    used_same = cursor.fetchone()[0] > 0
    total_distinct = prior_distinct + (0 if used_same else 1)
    if total_distinct >= threshold:
        return True, f"R010: Device switching — user {ctx['user_id']} used {total_distinct} distinct devices within {interval}"
    return False, None


def check_r011(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Blacklisted Phone Number."""
    phone = ctx.get("phone_number")
    if not phone: return False, None
    cursor.execute("SELECT reason FROM master.phone_blacklist WHERE phone_number = %s AND is_active = TRUE", (phone,))
    row = cursor.fetchone()
    if row:
        return True, f"R011: Phone number {phone} is blacklisted ({row[0]})"
    return False, None


def check_r012(cursor: Any, ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Blacklisted Email."""
    cursor.execute("SELECT reason FROM master.email_blacklist WHERE email = %s AND is_active = TRUE", (ctx["email"],))
    row = cursor.fetchone()
    if row:
        return True, f"R012: Email {ctx['email']} is blacklisted ({row[0]})"
    return False, None


def clear_interval_cache(rule_id: Optional[str] = None):
    """Clears both interval and threshold caches."""
    global _INTERVAL_CACHE, _THRESHOLD_CACHE
    if rule_id:
        _INTERVAL_CACHE.pop(rule_id, None)
        _THRESHOLD_CACHE.pop(rule_id, None)
    else:
        _INTERVAL_CACHE.clear()
        _THRESHOLD_CACHE.clear()


# Ordered rule set
RULE_CHECKS: List[Tuple[str, Callable]] = [
    ("R001", check_r001), ("R002", check_r002), ("R003", check_r003),
    ("R004", check_r004), ("R005", check_r005), ("R006", check_r006),
    ("R007", check_r007), ("R008", check_r008), ("R009", check_r009),
    ("R010", check_r010), ("R011", check_r011), ("R012", check_r012),
]