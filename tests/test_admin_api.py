from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ---------------- create analyst ----------------

@patch("api.admin.psycopg2.connect")
def test_create_analyst(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "analyst_id": "A001",
        "employee_name": "Vinay",
        "username": "vinay",
        "password": "password",
        "role": "Admin",
        "actor_role": "Admin",
    }

    response = client.post("/create-analyst", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Analyst Vinay Created"


# ---------------- blacklist ip ----------------

@patch("api.admin.psycopg2.connect")
def test_blacklist_ip(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "ip_address": "192.168.1.10",
        "reason": "Fraud Activity",
        "blacklisted_by": "A001",
    }

    response = client.post("/blacklist-ip", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "IP Blacklisted"


# ---------------- whitelist ip ----------------

@patch("api.admin.psycopg2.connect")
def test_whitelist_ip(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "removed_by": "A001",
        "removed_at": "2026-07-08 10:00:00",
        "blacklist_id": 1,
    }

    response = client.put("/whitelist-ip", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "IP Whitelisted"


# ---------------- update permissions ----------------

@patch("api.admin.psycopg2.connect")
@patch("api.admin.execute_batch")
def test_update_permissions_bulk(mock_execute_batch, mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    payload = {
        "analyst_id": "A001",
        "permissions": {
            "ADMIN_PANEL": True,
            "REPORTS": False,
        },
        "granted_by": "ADMIN",
    }

    response = client.put("/permissions/bulk", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully updated 2 permissions."

    mock_execute_batch.assert_called_once()