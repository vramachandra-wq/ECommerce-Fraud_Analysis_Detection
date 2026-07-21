from unittest.mock import MagicMock, patch

import requests

from portals.customer_portal import (
    _build_api_url,
    _send_api_request,
    fetch_form_options,
)


def test_build_api_url():
    with patch("portals.customer_portal.API_BASE_URL", "http://127.0.0.1:8000"):
        assert _build_api_url("create-order") == "http://127.0.0.1:8000/create-order"
        assert _build_api_url("/create-order") == "http://127.0.0.1:8000/create-order"


@patch("portals.customer_portal.requests.post")
def test_send_api_request_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    with patch("portals.customer_portal.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.customer_portal.API_TIMEOUT", 10):
            result = _send_api_request("post", "create-order", json={"order_id": "ORD001"})

    assert result is mock_resp
    mock_post.assert_called_once()


@patch("portals.customer_portal.st")
@patch("portals.customer_portal.requests.post")
def test_send_api_request_connection_error(mock_post, mock_st):
    mock_post.side_effect = requests.exceptions.ConnectionError("down")

    with patch("portals.customer_portal.API_BASE_URL", "http://127.0.0.1:8000"):
        with patch("portals.customer_portal.API_TIMEOUT", 10):
            result = _send_api_request("post", "create-order", json={})

    assert result is None
    mock_st.error.assert_called()


@patch("portals.customer_portal.list_devices")
@patch("portals.customer_portal.list_programs")
@patch("portals.customer_portal.list_products")
@patch("portals.customer_portal.get_cursor")
def test_fetch_form_options(mock_get_cursor, mock_products, mock_programs, mock_devices):
    fetch_form_options.clear()

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_cursor.return_value.__enter__.return_value = (mock_conn, mock_cur)

    mock_products.return_value = [("PR001", "Laptop", "Electronics", 1000)]
    mock_programs.return_value = [("P1", "Standard")]
    mock_devices.return_value = [("DEV001", "Phone", "Mobile")]

    products, programs, devices = fetch_form_options()

    assert products[0][0] == "PR001"
    assert programs[0][0] == "P1"
    assert devices[0][0] == "DEV001"
    mock_products.assert_called_once_with(mock_cur)
    mock_programs.assert_called_once_with(mock_cur)
    mock_devices.assert_called_once_with(mock_cur)
