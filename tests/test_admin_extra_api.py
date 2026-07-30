from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.auth import get_current_session
from api.main import app
from auth.analyst_auth import ALL_PAGES, PAGE_ADMIN_PANEL, PAGE_FRAUD_DASHBOARD
from tests.conftest import make_analyst_session

client = TestClient(app)


def _auth(role="Admin", pages=None, analyst_id="A001"):
    session = make_analyst_session(role=role, pages=pages or list(ALL_PAGES), analyst_id=analyst_id)

    def _dep():
        return session

    app.dependency_overrides[get_current_session] = _dep
    return session


def _clear():
    app.dependency_overrides.pop(get_current_session, None)


def _mock_db(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_create_analyst_forbidden_for_non_admin_actor():
    _auth(role="Fraud Analyst", pages=[PAGE_ADMIN_PANEL, PAGE_FRAUD_DASHBOARD])
    try:
        payload = {
            "analyst_id": "A099",
            "employee_name": "New Admin",
            "username": "newadmin",
            "password": "password",
            "role": "Admin",
        }
        response = client.post("/create-analyst", json=payload)
        assert response.status_code == 403
        assert "Only Admin" in response.json()["detail"]
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_blacklist_phone(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "phone_number": "9876543210",
            "reason": "Fraud Activity",
            "blacklisted_by": "A001",
        }
        response = client.post("/blacklist-phone", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Phone Blacklisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_whitelist_phone(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "removed_by": "A001",
            "removed_at": "2026-07-08 10:00:00",
            "blacklist_id": 1,
        }
        response = client.put("/whitelist-phone", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Phone Whitelisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_blacklist_email(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "email": "bad@example.com",
            "reason": "Fraud Activity",
            "blacklisted_by": "A001",
        }
        response = client.post("/blacklist-email", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Email Blacklisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.psycopg2.connect")
def test_whitelist_email(mock_connect, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "removed_by": "A001",
            "removed_at": "2026-07-08 10:00:00",
            "blacklist_id": 2,
        }
        response = client.put("/whitelist-email", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Email Whitelisted"
    finally:
        _clear()


@patch("api.admin.log_system_event")
@patch("api.admin.clear_metadata_cache")
@patch("api.admin.clear_interval_cache")
@patch("api.admin.psycopg2.connect")
def test_update_rule(mock_connect, mock_clear_interval, mock_clear_meta, mock_log):
    _auth()
    try:
        _mock_db(mock_connect)
        payload = {
            "rule_id": "R002",
            "action": "REVIEW",
            "threshold_value": 5,
            "time_interval_value": 1,
            "time_interval_unit": "HOUR",
        }
        response = client.put("/update-rule", json=payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Rule R002 updated successfully"
        mock_clear_interval.assert_called_once_with("R002")
        mock_clear_meta.assert_called_once_with("R002")
    finally:
        _clear()


@patch("api.admin.psycopg2.connect")
def test_blacklist_phone_database_error(mock_connect):
    _auth()
    try:
        mock_connect.side_effect = Exception("Database Error")
        response = client.post(
            "/blacklist-phone",
            json={
                "phone_number": "9876543210",
                "reason": "Fraud",
                "blacklisted_by": "A001",
            },
        )
        assert response.status_code == 500
    finally:
        _clear()
