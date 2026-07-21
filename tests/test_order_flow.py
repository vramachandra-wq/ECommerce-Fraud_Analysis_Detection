"""Order flow: fraud engine disposition -> create-order API payload."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from fraud_engine.engine import clear_metadata_cache, evaluate_order

client = TestClient(app)


def setup_function():
    clear_metadata_cache()


def _base_order_fields():
    return {
        "order_id": "ORD-000100",
        "user_id": "U001",
        "program_id": "P1",
        "product_id": "PR001",
        "category": "Electronics",
        "product_name": "Laptop",
        "quantity": 1,
        "amount": 1000.0,
        "ip_address": "1.1.1.1",
        "device_id": "DEV001",
        "customer_name": "John",
        "email": "john@test.com",
        "address": "12 Street, Chennai, TN 600001",
        "street": "12 Street",
        "city": "Chennai",
        "state": "TN",
        "country": "India",
        "zip_code": "600001",
        "phone_number": "9999999999",
        "order_timestamp": "2026-07-08 10:00:00",
    }


@patch("api.orders.psycopg2.connect")
def test_approved_disposition_posts_create_order(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("fraud_engine.engine.RULE_CHECKS", []):
        disposition = evaluate_order(None, {})

    payload = {
        **_base_order_fields(),
        "delay_minutes": disposition["delay_minutes"],
        "is_fraud": disposition["is_fraud"],
        "flagged_reason": disposition["flagged_reason"],
        "order_status": disposition["order_status"],
        "order_approved_at": "2026-07-08 10:00:00",
        "order_rejected_at": None,
        "triggered_rules": disposition["triggered_rules"],
    }

    assert disposition["order_status"] == "APPROVED"
    assert disposition["is_fraud"] is False

    response = client.post("/create-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Order Created successfully"


@patch("api.orders.execute_batch")
@patch("api.orders.psycopg2.connect")
def test_review_disposition_posts_triggered_rules(mock_connect, mock_execute_batch):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    def r002(cursor, ctx):
        return True, "R002: Email Velocity — 4 orders"

    cursor = MagicMock()
    cursor.fetchone.return_value = ("REVIEW", 0, "MINUTE")

    with patch("fraud_engine.engine.RULE_CHECKS", [("R002", r002)]):
        disposition = evaluate_order(cursor, {})

    assert disposition["order_status"] == "PENDING_REVIEW"
    assert len(disposition["triggered_rules"]) == 1
    assert disposition["triggered_rules"][0]["rule_id"] == "R002"

    payload = {
        **_base_order_fields(),
        "delay_minutes": disposition["delay_minutes"],
        "is_fraud": disposition["is_fraud"],
        "flagged_reason": disposition["flagged_reason"],
        "order_status": disposition["order_status"],
        "order_approved_at": None,
        "order_rejected_at": None,
        "triggered_rules": disposition["triggered_rules"],
    }

    response = client.post("/create-order", json=payload)

    assert response.status_code == 200
    mock_execute_batch.assert_called_once()


@patch("api.orders.execute_batch")
@patch("api.orders.psycopg2.connect")
def test_rejected_disposition_posts_fraud_flag(mock_connect, mock_execute_batch):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    def r007(cursor, ctx):
        return True, "R007: IP is blacklisted"

    cursor = MagicMock()
    cursor.fetchone.return_value = ("REJECTED", 0, "MINUTE")

    with patch("fraud_engine.engine.RULE_CHECKS", [("R007", r007)]):
        disposition = evaluate_order(cursor, {})

    assert disposition["order_status"] == "REJECTED"
    assert disposition["is_fraud"] is True

    payload = {
        **_base_order_fields(),
        "delay_minutes": disposition["delay_minutes"],
        "is_fraud": disposition["is_fraud"],
        "flagged_reason": disposition["flagged_reason"],
        "order_status": disposition["order_status"],
        "order_approved_at": None,
        "order_rejected_at": "2026-07-08 10:00:00",
        "triggered_rules": disposition["triggered_rules"],
    }

    response = client.post("/create-order", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Order Created successfully"
    mock_execute_batch.assert_called_once()
