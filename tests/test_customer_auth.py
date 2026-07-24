"""Tests for customer password change."""
from unittest.mock import MagicMock

from auth.customer_auth import change_customer_password
from auth.passwords import hash_password, verify_password


def test_change_customer_password_success():
    cur = MagicMock()
    conn = MagicMock()
    cur.fetchone.return_value = ("U1001", hash_password("password123"))

    ok, key = change_customer_password(
        cur,
        conn,
        user_id="U1001",
        current_password="password123",
        new_password="newpass99",
        confirm_password="newpass99",
    )
    assert ok is True
    assert key == "password_change_success"
    assert cur.execute.call_count >= 2
    args = cur.execute.call_args_list[-1][0]
    assert "UPDATE master.customers" in args[0]
    new_hash = args[1][0]
    assert verify_password("newpass99", new_hash)
    conn.commit.assert_called_once()


def test_change_customer_password_wrong_current():
    cur = MagicMock()
    conn = MagicMock()
    cur.fetchone.return_value = ("U1001", hash_password("password123"))

    ok, key = change_customer_password(
        cur,
        conn,
        user_id="U1001",
        current_password="wrong",
        new_password="newpass99",
        confirm_password="newpass99",
    )
    assert ok is False
    assert key == "password_change_wrong_current"
    conn.commit.assert_not_called()


def test_change_customer_password_mismatch():
    cur = MagicMock()
    conn = MagicMock()
    ok, key = change_customer_password(
        cur,
        conn,
        user_id="U1001",
        current_password="password123",
        new_password="newpass99",
        confirm_password="otherpass",
    )
    assert ok is False
    assert key == "password_change_mismatch"
