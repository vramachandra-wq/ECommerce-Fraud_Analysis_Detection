from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call

import pandas as pd

from fraud_engine.auto_approval import sync_expired_holds
from fraud_engine.backlog import (
    compute_deadline,
    detect_backlog_orders,
    is_backlog_order,
)


def test_is_backlog_order_true_when_elapsed():
    tagged = datetime(2026, 1, 1, 12, 0, 0)
    now = tagged + timedelta(minutes=60)
    assert is_backlog_order(tagged, delay_minutes=60, now=now) is True


def test_is_backlog_order_false_before_deadline():
    tagged = datetime(2026, 1, 1, 12, 0, 0)
    now = tagged + timedelta(minutes=59)
    assert is_backlog_order(tagged, delay_minutes=60, now=now) is False


def test_compute_deadline():
    tagged = datetime(2026, 1, 1, 10, 0, 0)
    assert compute_deadline(tagged, 180) == datetime(2026, 1, 1, 13, 0, 0)


def test_sync_expired_holds_uses_backlog_lock():
    conn = MagicMock()
    cursor = MagicMock()

    with patch(
        "fraud_engine.auto_approval.lock_backlog_order_ids",
        return_value=["ORD-1", "ORD-2"],
    ) as lock_mock, patch(
        "fraud_engine.auto_approval.fetch_order_audit_context",
        return_value={"rule_name": "P2 iPhone 16 Rule", "delay_minutes": 180},
    ), patch(
        "fraud_engine.auto_approval.log_review_action",
    ) as log_mock:
        cursor.rowcount = 1
        updated = sync_expired_holds(conn, cursor)

    lock_mock.assert_called_once_with(cursor, order_ids=None)
    assert updated == 2
    assert cursor.execute.call_count == 2  # two UPDATEs
    assert log_mock.call_count == 2


def test_sync_expired_holds_no_backlog():
    conn = MagicMock()
    cursor = MagicMock()

    with patch(
        "fraud_engine.auto_approval.lock_backlog_order_ids",
        return_value=[],
    ):
        updated = sync_expired_holds(conn, cursor)

    assert updated == 0
    cursor.execute.assert_not_called()


def test_detect_backlog_orders_builds_dataframe():
    cursor = MagicMock()
    cursor.description = [
        MagicMock(name=n)
        for n in [
            "order_id",
            "user_id",
            "customer_name",
            "product_name",
            "amount",
            "order_status",
            "flagged_reason",
            "tagged_timestamp",
            "order_delay_minutes",
            "delay_minutes",
            "rule_name",
            "review_deadline",
            "minutes_remaining",
        ]
    ]
    # Fix MagicMock name attribute — use simple objects
    class Col:
        def __init__(self, name):
            self.name = name

    cursor.description = [
        Col(n)
        for n in [
            "order_id",
            "user_id",
            "customer_name",
            "product_name",
            "amount",
            "order_status",
            "flagged_reason",
            "tagged_timestamp",
            "order_delay_minutes",
            "delay_minutes",
            "rule_name",
            "review_deadline",
            "minutes_remaining",
        ]
    ]
    cursor.fetchall.return_value = [
        (
            "ORD-1",
            "U1",
            "Alice",
            "iPhone",
            1000,
            "ON_HOLD",
            "R001",
            datetime(2026, 1, 1, 10, 0, 0),
            180,
            180,
            "P2 iPhone 16 Rule",
            datetime(2026, 1, 1, 13, 0, 0),
            -30.0,
        )
    ]

    df = detect_backlog_orders(cursor)
    assert len(df) == 1
    assert df.iloc[0]["order_id"] == "ORD-1"
    assert bool(df.iloc[0]["is_overdue"]) is True
    assert float(df.iloc[0]["minutes_overdue"]) == 30.0
