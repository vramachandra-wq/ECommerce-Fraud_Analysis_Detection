from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


# ---------------- create-order ----------------

@patch("api.orders.psycopg2.connect")
def test_create_order_success(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    payload = {
        "order_id": "ORD001",
        "user_id": "U001",
        "program_id": "P1",
        "product_id": "PR001",
        "category": "Electronics",
        "product_name": "Laptop",
        "quantity": 1,
        "amount": 1000,
        "ip_address": "1.1.1.1",
        "device_id": "DEV001",
        "customer_name": "John",
        "email": "john@test.com",
        "address": "Chennai",
        "street": "ABC",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "zip_code": "600001",
        "phone_number": "9999999999",
        "order_timestamp": "2026-07-08 10:00:00",
        "delay_minutes": 0,
        "is_fraud": False,
        "flagged_reason": None,
        "order_status": "APPROVED",
        "order_approved_at": None,
        "order_rejected_at": None,
        "triggered_rules": []
    }

    response = client.post("/create-order", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Order Created successfully"
    }


@patch("api.orders.psycopg2.connect")
def test_create_order_database_exception(mock_connect):
    mock_connect.side_effect = Exception("Database Error")

    response = client.post("/create-order", json={})

    assert response.status_code == 500


