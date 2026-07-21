from unittest.mock import MagicMock

from fraud_engine.auto_approval import sync_expired_holds


def test_sync_expired_holds_updates_orders():
    conn = MagicMock()
    cursor = MagicMock()

    cursor.rowcount = 5

    updated = sync_expired_holds(conn, cursor)

    cursor.execute.assert_called_once()
    assert updated == 5


def test_sync_expired_holds_no_orders():
    conn = MagicMock()
    cursor = MagicMock()

    cursor.rowcount = 0

    updated = sync_expired_holds(conn, cursor)

    cursor.execute.assert_called_once()
    assert updated == 0