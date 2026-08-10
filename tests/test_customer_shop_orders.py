"""Customer shop order history API tests (mocked DB)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.customer_shop import get_current_customer
from api.main import app

client = TestClient(app)

CUSTOMER = {
    "user_id": "U1",
    "customer_name": "Test Buyer",
    "email": "buyer@example.com",
    "phone_number": "+66999999999",
    "street": "1 Main",
    "city": "Bangkok",
    "state": "Bangkok",
    "zip_code": "10110",
    "country": "Thailand",
}


def _override_customer():
    app.dependency_overrides[get_current_customer] = lambda: CUSTOMER


def _clear_overrides():
    app.dependency_overrides.pop(get_current_customer, None)


def test_shop_list_orders_requires_auth():
    _clear_overrides()
    response = client.get("/shop/orders")
    assert response.status_code == 401


def test_shop_list_orders_returns_customer_history():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    ts = datetime(2026, 8, 1, 12, 30, 0)
    mock_cur.fetchone.return_value = (2,)
    mock_cur.fetchall.return_value = [
        ("ORD-2", "P2", "Phone", "Electronics", 1, 1999.0, "APPROVED", ts, 1),
        ("ORD-1", "P1", "Bundle", "Electronics", 3, 500.0, "PENDING_REVIEW", ts, 2),
    ]

    _override_customer()
    try:
        with patch("api.customer_shop.psycopg2.connect", return_value=mock_conn), patch(
            "api.customer_shop.ensure_order_items_table"
        ):
            response = client.get("/shop/orders")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["orders"]) == 2
    assert body["orders"][0]["order_id"] == "ORD-2"
    assert body["orders"][0]["amount"] == 1999.0
    assert body["orders"][0]["order_status"] == "APPROVED"
    assert body["orders"][1]["item_count"] == 2
    assert "2026-08-01" in body["orders"][0]["order_timestamp"]


def test_shop_list_orders_empty():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (0,)
    mock_cur.fetchall.return_value = []

    _override_customer()
    try:
        with patch("api.customer_shop.psycopg2.connect", return_value=mock_conn), patch(
            "api.customer_shop.ensure_order_items_table"
        ):
            response = client.get("/shop/orders", params={"limit": 10, "offset": 0})
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert response.json() == {
        "orders": [],
        "total": 0,
        "limit": 10,
        "offset": 0,
    }


def test_shop_get_order_still_scoped_to_customer():
    """Existing detail endpoint remains; other customers get 404."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (
        "ORD-9",
        "OTHER",
        "P1",
        "Widget",
        "Electronics",
        1,
        10.0,
        "APPROVED",
        None,
        datetime(2026, 8, 1, 10, 0, 0),
        "9 Other St",
        "Bangkok",
        "Bangkok",
        "10110",
        "Thailand",
        "9 Other St, Bangkok",
    )

    _override_customer()
    try:
        with patch("api.customer_shop.psycopg2.connect", return_value=mock_conn), patch(
            "api.customer_shop.ensure_order_items_table"
        ), patch("api.customer_shop.fetch_order_items", return_value=[]):
            response = client.get("/shop/orders/ORD-9")
    finally:
        _clear_overrides()

    assert response.status_code == 404


def test_shop_get_order_includes_delivery_address():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (
        "ORD-1",
        "U1",
        "P1",
        "Widget",
        "Electronics",
        2,
        20.0,
        "APPROVED",
        None,
        datetime(2026, 8, 1, 10, 0, 0),
        "12 Sukhumvit",
        "Bangkok",
        "Bangkok",
        "10110",
        "Thailand",
        "12 Sukhumvit, Bangkok",
    )

    _override_customer()
    try:
        with patch("api.customer_shop.psycopg2.connect", return_value=mock_conn), patch(
            "api.customer_shop.ensure_order_items_table"
        ), patch(
            "api.customer_shop.fetch_order_items",
            return_value=[
                {
                    "line_no": 1,
                    "product_id": "P1",
                    "product_name": "Widget",
                    "quantity": 2,
                    "line_amount": 20.0,
                }
            ],
        ):
            response = client.get("/shop/orders/ORD-1")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "ORD-1"
    assert body["quantity"] == 2
    assert body["delivery_address"] == "12 Sukhumvit, Bangkok, Bangkok, 10110, Thailand"
    assert body["street"] == "12 Sukhumvit"
