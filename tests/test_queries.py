from unittest.mock import MagicMock

import pandas as pd

from utils.queries import (
    list_products,
    list_programs,
    list_devices,
    get_queue_orders,
    get_order_detail,
    get_recent_orders,
    get_kpis,
    get_rule_stats,
    get_active_blacklist_entry,
    get_active_phone_blacklist_entry,
    get_active_email_blacklist_entry,
    get_orders_over_time,
    get_permission_matrix,
    get_analyst_performance,
)
# ---------- list functions ----------

def test_list_products():
    cursor = MagicMock()

    cursor.fetchall.return_value = [
        ("P001", "Laptop", "Electronics", 1000)
    ]

    result = list_products(cursor)

    assert len(result) == 1
    cursor.execute.assert_called_once()


def test_list_programs():
    cursor = MagicMock()

    cursor.fetchall.return_value = [
        ("P1", "Premium")
    ]

    result = list_programs(cursor)

    assert result[0][0] == "P1"


def test_list_devices():
    cursor = MagicMock()

    cursor.fetchall.return_value = [
        ("DEV001", "iPhone", "Mobile")
    ]

    result = list_devices(cursor)

    assert result[0][1] == "iPhone"


# ---------- dataframe functions ----------

def test_get_queue_orders():
    cursor = MagicMock()

    cursor.description = [
        MagicMock(name="order_id"),
        MagicMock(name="order_status"),
    ]

    cursor.description[0].name = "order_id"
    cursor.description[1].name = "order_status"

    cursor.fetchall.return_value = [
        ("ORD001", "ON_HOLD")
    ]

    df = get_queue_orders(cursor)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_get_recent_orders():
    cursor = MagicMock()

    cols = [
        "order_id",
        "user_id",
        "customer_name",
        "product_name",
        "quantity",
        "amount",
        "order_status",
        "delay_minutes",
        "is_fraud",
        "order_timestamp",
        "order_approved_at",
        "order_rejected_at",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchall.return_value = [
        (
            "ORD001",
            "U001",
            "John",
            "Laptop",
            1,
            1000,
            "APPROVED",
            0,
            False,
            "2026",
            None,
            None,
        )
    ]

    df = get_recent_orders(cursor)

    assert isinstance(df, pd.DataFrame)


def test_get_rule_stats():
    cursor = MagicMock()

    cols = [
        "rule_id",
        "rule_name",
        "action",
        "threshold_value",
        "times_triggered",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchall.return_value = [
        ("R001", "Rule1", "HOLD", 1, 10)
    ]

    df = get_rule_stats(cursor)

    assert isinstance(df, pd.DataFrame)


def test_get_orders_over_time():
    cursor = MagicMock()

    cols = ["order_date", "order_count"]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchall.return_value = [
        ("2026-07-08", 10)
    ]

    df = get_orders_over_time(cursor)

    assert isinstance(df, pd.DataFrame)


def test_get_analyst_performance():
    cursor = MagicMock()

    cols = [
        "analyst_id",
        "employee_name",
        "role",
        "orders_reviewed",
        "orders_rejected",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchall.return_value = [
        ("A001", "Vinay", "Admin", 50, 5)
    ]

    df = get_analyst_performance(cursor)

    assert isinstance(df, pd.DataFrame)


# ---------- dictionary functions ----------

def test_get_order_detail_found():
    cursor = MagicMock()

    cursor.description = []

    for c in ["order_id", "customer_name"]:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchone.return_value = (
        "ORD001",
        "John",
    )

    result = get_order_detail(cursor, "ORD001")

    assert result["order_id"] == "ORD001"


def test_get_order_detail_not_found():
    cursor = MagicMock()

    cursor.fetchone.return_value = None

    result = get_order_detail(cursor, "ORD001")

    assert result is None


def test_get_active_blacklist_entry_found():
    cursor = MagicMock()

    cols = [
        "blacklist_id",
        "ip_address",
        "reason",
        "blacklisted_by",
        "blacklisted_by_name",
        "blacklisted_at",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchone.return_value = (
        1,
        "1.1.1.1",
        "Fraud",
        "A001",
        "Vinay",
        "Today",
    )

    result = get_active_blacklist_entry(cursor, "1.1.1.1")

    assert result["reason"] == "Fraud"


def test_get_active_blacklist_entry_not_found():
    cursor = MagicMock()

    cursor.fetchone.return_value = None

    result = get_active_blacklist_entry(cursor, "1.1.1.1")

    assert result is None


# ---------- KPI ----------

def test_get_kpis():
    cursor = MagicMock()

    cursor.fetchone.side_effect = [
        [100],
        [10],
    ]

    cursor.fetchall.return_value = [
        ("APPROVED", 80),
        ("REJECTED", 20),
    ]

    result = get_kpis(cursor)

    assert result["total_orders"] == 100
    assert result["total_fraud"] == 10
    assert result["status_counts"]["APPROVED"] == 80




# ---------- permission matrix ----------

def test_get_permission_matrix():
    cursor = MagicMock()

    cols = [
        "analyst_id",
        "employee_name",
        "username",
        "role",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchall.side_effect = [
        [
            ("A001", "Vinay", "vinay", "Analyst"),
        ],
        [
            ("A001", "ADMIN_PANEL"),
        ],
    ]

    result = get_permission_matrix(cursor)

    assert result[0]["analyst_id"] == "A001"
    assert "ADMIN_PANEL" in result[0]["granted_pages"]




# ---------- blacklist functions ----------
def test_get_active_phone_blacklist_entry_found():
    cursor = MagicMock()

    cols = [
        "blacklist_id",
        "phone_number",
        "reason",
        "blacklisted_by",
        "blacklisted_by_name",
        "blacklisted_at",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchone.return_value = (
        1,
        "9876543210",
        "Fraud",
        "A001",
        "Vinay",
        "Today",
    )

    result = get_active_phone_blacklist_entry(cursor, "9876543210")

    assert result["reason"] == "Fraud"
    assert result["phone_number"] == "9876543210"


def test_get_active_phone_blacklist_entry_not_found():
    cursor = MagicMock()

    cursor.fetchone.return_value = None

    result = get_active_phone_blacklist_entry(cursor, "9876543210")

    assert result is None


def test_get_active_email_blacklist_entry_found():
    cursor = MagicMock()

    cols = [
        "blacklist_id",
        "email",
        "reason",
        "blacklisted_by",
        "blacklisted_by_name",
        "blacklisted_at",
    ]

    cursor.description = []

    for c in cols:
        obj = MagicMock()
        obj.name = c
        cursor.description.append(obj)

    cursor.fetchone.return_value = (
        1,
        "john@example.com",
        "Fraud",
        "A001",
        "Vinay",
        "Today",
    )

    result = get_active_email_blacklist_entry(cursor, "john@example.com")

    assert result["reason"] == "Fraud"
    assert result["email"] == "john@example.com"


def test_get_active_email_blacklist_entry_not_found():
    cursor = MagicMock()

    cursor.fetchone.return_value = None

    result = get_active_email_blacklist_entry(cursor, "john@example.com")

    assert result is None    