from unittest.mock import MagicMock, patch

import requests

from auth.analyst_auth import (
    can_create_admin_users,
    creatable_roles_for,
    CREATABLE_ROLES_ADMIN,
    CREATABLE_ROLES_NON_ADMIN,
)
from portals.admin_panel import (
    _build_api_url,
    _generate_rule_description,
    _send_api_request,
    sync_database_holds,
)


def test_build_api_url():
    with patch("portals.admin_panel.API_BASE_URL", "http://127.0.0.1:8000"):
        assert _build_api_url("create-analyst") == "http://127.0.0.1:8000/create-analyst"


@patch("portals.admin_panel.requests.post")
def test_send_api_request_post_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    with patch("portals.admin_panel.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.admin_panel.API_TIMEOUT", 10):
            result = _send_api_request("post", "create-analyst", {"analyst_id": "A001"})

    assert result is mock_resp


@patch("portals.admin_panel.st")
@patch("portals.admin_panel.requests.put")
def test_send_api_request_non_200(mock_put, mock_st):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "fail"
    mock_put.return_value = mock_resp

    with patch("portals.admin_panel.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.admin_panel.API_TIMEOUT", 10):
            result = _send_api_request("put", "update-rule", {"rule_id": "R001"})

    assert result is None
    mock_st.error.assert_called()


@patch("portals.admin_panel.st")
@patch("portals.admin_panel.requests.post")
def test_send_api_request_connection_error(mock_post, mock_st):
    mock_post.side_effect = requests.exceptions.ConnectionError("down")

    with patch("portals.admin_panel.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.admin_panel.API_TIMEOUT", 10):
            result = _send_api_request("post", "blacklist-ip", {})

    assert result is None
    mock_st.error.assert_called()


def test_generate_rule_description_r001():
    desc = _generate_rule_description(
        {
            "rule_id": "R001",
            "rule_name": "iPhone Rule",
            "action": "HOLD",
        }
    )
    assert "P2 iPhone 16" in desc
    assert "HOLD" in desc


def test_generate_rule_description_blacklist():
    desc = _generate_rule_description(
        {
            "rule_id": "R007",
            "rule_name": "Blacklisted IP",
            "action": "REJECTED",
        }
    )
    assert "blacklisted" in desc.lower()
    assert "REJECTED" in desc


def test_generate_rule_description_velocity():
    desc = _generate_rule_description(
        {
            "rule_id": "R002",
            "rule_name": "Email Velocity",
            "rule_type": "VELOCITY",
            "action": "REVIEW",
            "threshold_value": 3,
            "time_interval_value": 1,
            "time_interval_unit": "HOUR",
        }
    )
    assert "REVIEW" in desc
    assert "3" in desc
    assert "1" in desc


def test_generate_rule_description_linkage():
    desc = _generate_rule_description(
        {
            "rule_id": "R006",
            "rule_name": "Email Linkage",
            "rule_type": "LINKAGE",
            "action": "REVIEW",
            "threshold_value": 1,
        }
    )
    assert "linked entities" in desc
    assert "1" in desc


@patch("portals.admin_panel.sync_expired_holds")
@patch("portals.admin_panel.get_cursor")
def test_sync_database_holds_wires_auto_approval(mock_get_cursor, mock_sync):
    sync_database_holds.clear()

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_cursor.return_value.__enter__.return_value = (mock_conn, mock_cur)

    sync_database_holds()

    mock_get_cursor.assert_called_once_with(commit=True)
    mock_sync.assert_called_once_with(mock_conn, mock_cur)


def test_can_create_admin_users():
    assert can_create_admin_users({"role": "Admin"}) is True
    assert can_create_admin_users({"role": "Fraud Analyst"}) is False


def test_creatable_roles_for_admin_and_non_admin():
    assert creatable_roles_for({"role": "Admin"}) == CREATABLE_ROLES_ADMIN
    assert creatable_roles_for({"role": "Fraud Analyst"}) == CREATABLE_ROLES_NON_ADMIN
