from unittest.mock import MagicMock, patch

import requests

from portals.analyst_dashboard import (
    _build_api_url,
    _send_api_request,
    sync_database_holds,
)


def test_build_api_url():
    with patch("portals.analyst_dashboard.API_BASE_URL", "http://127.0.0.1:8000/"):
        assert _build_api_url("approve-order") == "http://127.0.0.1:8000/approve-order"
        assert _build_api_url("/reject-order") == "http://127.0.0.1:8000/reject-order"


@patch("portals.analyst_dashboard.requests.put")
def test_send_api_request_put_success(mock_put):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_put.return_value = mock_resp

    with patch("portals.analyst_dashboard.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.analyst_dashboard.API_TIMEOUT", 10):
            result = _send_api_request(
                "put",
                "approve-order",
                json={"order_id": "ORD001"},
            )

    assert result is mock_resp
    mock_put.assert_called_once()


@patch("portals.analyst_dashboard.st")
@patch("portals.analyst_dashboard.requests.post")
def test_send_api_request_http_error_body(mock_post, mock_st):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    mock_resp.text = "Database error"
    mock_post.return_value = mock_resp

    with patch("portals.analyst_dashboard.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.analyst_dashboard.API_TIMEOUT", 10):
            result = _send_api_request("post", "blacklist-ip", json={})

    assert result is mock_resp
    mock_st.error.assert_called_with("Database error")


@patch("portals.analyst_dashboard.st")
@patch("portals.analyst_dashboard.requests.put")
def test_send_api_request_timeout(mock_put, mock_st):
    mock_put.side_effect = requests.exceptions.Timeout("timed out")

    with patch("portals.analyst_dashboard.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.analyst_dashboard.API_TIMEOUT", 10):
            result = _send_api_request("put", "approve-order", json={})

    assert result is None
    mock_st.error.assert_called()


@patch("portals.analyst_dashboard.sync_expired_holds")
@patch("portals.analyst_dashboard.get_cursor")
def test_sync_database_holds_calls_auto_approval(mock_get_cursor, mock_sync):
    sync_database_holds.clear()

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_cursor.return_value.__enter__.return_value = (mock_conn, mock_cur)
    mock_sync.return_value = 3

    updated = sync_database_holds()

    assert updated == 3
    mock_get_cursor.assert_called_once_with(commit=True)
    mock_sync.assert_called_once_with(mock_conn, mock_cur)
