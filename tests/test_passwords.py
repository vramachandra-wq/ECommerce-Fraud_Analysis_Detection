from auth.passwords import (
    hash_password,
    verify_password,
    is_hashed,
    upgrade_password_if_needed,
)
from unittest.mock import MagicMock


def test_hash_password_is_bcrypt():
    hashed = hash_password("secret123")

    assert is_hashed(hashed)
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True


def test_verify_password_wrong_hash():
    hashed = hash_password("secret123")

    assert verify_password("wrong", hashed) is False


def test_verify_password_empty_stored():
    assert verify_password("anything", "") is False
    assert verify_password("anything", None) is False


def test_verify_password_legacy_plaintext():
    assert verify_password("legacy", "legacy") is True
    assert verify_password("legacy", "other") is False
    assert is_hashed("legacy") is False


def test_is_hashed_prefixes():
    assert is_hashed("$2b$12$abcdefghijklmnopqrstuv") is True
    assert is_hashed("$2a$12$abcdefghijklmnopqrstuv") is True
    assert is_hashed("$2y$12$abcdefghijklmnopqrstuv") is True
    assert is_hashed("plaintext") is False
    assert is_hashed("") is False


def test_upgrade_password_if_needed_skips_already_hashed():
    cursor = MagicMock()
    conn = MagicMock()
    hashed = hash_password("secret123")

    upgrade_password_if_needed(
        cursor,
        conn,
        table="master.customers",
        id_column="user_id",
        id_value="U001",
        plain_password="secret123",
        stored_password=hashed,
    )

    cursor.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_upgrade_password_if_needed_rehashes_plaintext():
    cursor = MagicMock()
    conn = MagicMock()

    upgrade_password_if_needed(
        cursor,
        conn,
        table="master.customers",
        id_column="user_id",
        id_value="U001",
        plain_password="secret123",
        stored_password="secret123",
    )

    cursor.execute.assert_called_once()
    args = cursor.execute.call_args[0]
    assert "UPDATE master.customers SET password" in args[0]
    new_hash = args[1][0]
    assert is_hashed(new_hash)
    assert args[1][1] == "U001"
    conn.commit.assert_called_once()
