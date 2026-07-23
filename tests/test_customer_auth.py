from unittest.mock import MagicMock, patch

from auth.customer_auth import authenticate_customer


def _customer_row(
    *,
    street="21 MG Road",
    city="Bengaluru",
    state="Karnataka",
    country="India",
    zip_code="560001",
):
    return (
        "U001",
        "John Doe",
        "john@example.com",
        "9876543210",
        "21 MG Road, Bengaluru, Karnataka 560001",
        street,
        city,
        state,
        country,
        zip_code,
        "P2",
        "hashed_password",
    )


# ---------- authenticate_customer ----------

@patch("auth.customer_auth.verify_password")
def test_authenticate_customer_success(mock_verify):
    mock_verify.return_value = True

    cursor = MagicMock()
    cursor.fetchone.return_value = _customer_row()

    customer = authenticate_customer(cursor, "U001", "password123")

    cursor.execute.assert_called_once()
    mock_verify.assert_called_once_with("password123", "hashed_password")

    assert customer["user_id"] == "U001"
    assert customer["customer_name"] == "John Doe"
    assert customer["email"] == "john@example.com"
    assert customer["phone_number"] == "9876543210"
    assert customer["default_address"] == "21 MG Road, Bengaluru, Karnataka 560001"
    assert customer["street"] == "21 MG Road"
    assert customer["city"] == "Bengaluru"
    assert customer["state"] == "Karnataka"
    assert customer["country"] == "India"
    assert customer["zip_code"] == "560001"
    assert customer["program_id"] == "P2"
    assert "password" not in customer


@patch("auth.customer_auth.verify_password")
def test_authenticate_customer_invalid_credentials(mock_verify):
    mock_verify.return_value = False

    cursor = MagicMock()
    cursor.fetchone.return_value = _customer_row()

    customer = authenticate_customer(cursor, "U001", "wrongpassword")

    cursor.execute.assert_called_once()
    assert customer is None


def test_authenticate_customer_user_not_found():
    cursor = MagicMock()
    cursor.fetchone.return_value = None

    customer = authenticate_customer(cursor, "U999", "password123")

    cursor.execute.assert_called_once()
    assert customer is None


@patch("auth.customer_auth.upgrade_password_if_needed")
@patch("auth.customer_auth.verify_password")
def test_authenticate_customer_upgrades_password_when_conn_provided(
    mock_verify, mock_upgrade
):
    mock_verify.return_value = True
    cursor = MagicMock()
    conn = MagicMock()

    cursor.fetchone.return_value = _customer_row()

    customer = authenticate_customer(cursor, "U001", "password123", conn=conn)

    assert customer["user_id"] == "U001"
    mock_upgrade.assert_called_once()
