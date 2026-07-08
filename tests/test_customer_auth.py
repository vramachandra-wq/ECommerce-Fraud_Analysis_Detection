from unittest.mock import MagicMock

from auth.customer_auth import authenticate_customer


def test_authenticate_customer_success():
    cursor = MagicMock()

    cursor.fetchone.return_value = (
        "U001",
        "John Doe",
        "john@example.com",
        "9876543210",
        "Chennai",
        "P2",
    )

    customer = authenticate_customer(cursor, "U001", "password123")

    cursor.execute.assert_called_once()

    assert customer["user_id"] == "U001"
    assert customer["customer_name"] == "John Doe"
    assert customer["email"] == "john@example.com"
    assert customer["program_id"] == "P2"


def test_authenticate_customer_invalid_credentials():
    cursor = MagicMock()

    cursor.fetchone.return_value = None

    customer = authenticate_customer(cursor, "U001", "wrongpassword")

    cursor.execute.assert_called_once()

    assert customer is None