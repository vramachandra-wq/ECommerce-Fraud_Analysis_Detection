from unittest.mock import MagicMock, patch

from auth.analyst_auth import (
    authenticate_analyst,
    change_analyst_password,
    is_admin,
    get_granted_pages,
    has_page_access,
    PAGE_FRAUD_DASHBOARD,
    PAGE_ADMIN_PANEL,
)
from auth.passwords import hash_password, is_hashed


# ---------- authenticate_analyst ----------

@patch("auth.analyst_auth.verify_password")
def test_authenticate_analyst_success(mock_verify):
    mock_verify.return_value = True

    cursor = MagicMock()

    cursor.fetchone.return_value = (
        "A001",
        "Vinay",
        "vinay",
        "Admin",
        "hashed_password",
    )

    analyst = authenticate_analyst(cursor, "vinay", "password")

    cursor.execute.assert_called_once()

    assert analyst["analyst_id"] == "A001"
    assert analyst["employee_name"] == "Vinay"
    assert analyst["username"] == "vinay"
    assert analyst["role"] == "Admin"


@patch("auth.analyst_auth.verify_password")
def test_authenticate_analyst_invalid_credentials(mock_verify):
    mock_verify.return_value = False

    cursor = MagicMock()

    cursor.fetchone.return_value = (
        "A001",
        "Vinay",
        "vinay",
        "Admin",
        "hashed_password",
    )

    analyst = authenticate_analyst(cursor, "vinay", "wrong")

    cursor.execute.assert_called_once()

    assert analyst is None


# ---------- is_admin ----------

def test_is_admin_true():
    analyst = {"role": "Admin"}

    assert is_admin(analyst) is True


def test_is_admin_false():
    analyst = {"role": "Analyst"}

    assert is_admin(analyst) is False


def test_is_admin_none():
    assert is_admin(None) is False


# ---------- get_granted_pages ----------

def test_get_granted_pages_admin():
    cursor = MagicMock()

    analyst = {
        "analyst_id": "A001",
        "role": "Admin",
    }

    pages = get_granted_pages(cursor, analyst)

    assert PAGE_FRAUD_DASHBOARD in pages
    assert PAGE_ADMIN_PANEL in pages


def test_get_granted_pages_non_admin():
    cursor = MagicMock()

    cursor.fetchall.return_value = [
        (PAGE_FRAUD_DASHBOARD,),
    ]

    analyst = {
        "analyst_id": "A002",
        "role": "Analyst",
    }

    pages = get_granted_pages(cursor, analyst)

    cursor.execute.assert_called_once()

    assert pages == {PAGE_FRAUD_DASHBOARD}


# ---------- has_page_access ----------

def test_has_page_access_true():
    granted_pages = {
        PAGE_FRAUD_DASHBOARD,
    }

    assert has_page_access(granted_pages, PAGE_FRAUD_DASHBOARD) is True


def test_has_page_access_false():
    granted_pages = {
        PAGE_FRAUD_DASHBOARD,
    }

    assert has_page_access(granted_pages, PAGE_ADMIN_PANEL) is False

# ---------- change_analyst_password ----------

def test_change_analyst_password_success():
    cursor = MagicMock()
    conn = MagicMock()
    stored = hash_password("oldpass12")
    cursor.fetchone.return_value = ("A1", stored)

    ok, key = change_analyst_password(
        cursor,
        conn,
        analyst_id="A1",
        current_password="oldpass12",
        new_password="newpass99",
        confirm_password="newpass99",
    )

    assert ok is True
    assert key == "password_change_success"
    update_sql = cursor.execute.call_args_list[-1][0][0]
    assert "UPDATE master.analyst_users" in update_sql
    new_hash = cursor.execute.call_args_list[-1][0][1][0]
    assert is_hashed(new_hash)
    conn.commit.assert_called_once()


def test_change_analyst_password_by_username_success():
    cursor = MagicMock()
    conn = MagicMock()
    stored = hash_password("oldpass12")
    cursor.fetchone.return_value = ("A1", stored)

    ok, key = change_analyst_password(
        cursor,
        conn,
        username="analyst",
        current_password="oldpass12",
        new_password="newpass99",
        confirm_password="newpass99",
    )

    assert ok is True
    assert key == "password_change_success"
    assert "WHERE username" in cursor.execute.call_args_list[0][0][0]


def test_change_analyst_password_wrong_current():
    cursor = MagicMock()
    conn = MagicMock()
    cursor.fetchone.return_value = ("A1", hash_password("oldpass12"))

    ok, key = change_analyst_password(
        cursor,
        conn,
        analyst_id="A1",
        current_password="wrongpass",
        new_password="newpass99",
        confirm_password="newpass99",
    )

    assert ok is False
    assert key == "password_change_wrong_current"
    conn.commit.assert_not_called()


def test_change_analyst_password_mismatch():
    cursor = MagicMock()
    conn = MagicMock()

    ok, key = change_analyst_password(
        cursor,
        conn,
        analyst_id="A1",
        current_password="oldpass12",
        new_password="newpass99",
        confirm_password="different1",
    )

    assert ok is False
    assert key == "password_change_mismatch"
    cursor.execute.assert_not_called()


def test_change_analyst_password_too_short():
    cursor = MagicMock()
    conn = MagicMock()

    ok, key = change_analyst_password(
        cursor,
        conn,
        analyst_id="A1",
        current_password="oldpass12",
        new_password="short",
        confirm_password="short",
    )

    assert ok is False
    assert key == "password_change_too_short"
