from typing import Any, Dict, Optional, Tuple

from auth.passwords import hash_password, upgrade_password_if_needed, verify_password

CUSTOMER_FIELDS = [
    "user_id",
    "customer_name",
    "email",
    "phone_number",
    "default_address",
    "street",
    "city",
    "state",
    "country",
    "zip_code",
    "program_id",
]

MIN_PASSWORD_LENGTH = 8


def authenticate_customer(
    cursor,
    user_id: str,
    password: str,
    conn=None,
) -> Optional[Dict[str, Any]]:
    """
    Validates customer credentials against the database.
    Returns a dictionary of customer details if successful, otherwise None.
    """
    cursor.execute(
        """
        SELECT
            user_id,
            customer_name,
            email,
            phone_number,
            default_address,
            street,
            city,
            state,
            country,
            zip_code,
            program_id,
            password
        FROM master.customers
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    data = dict(zip(CUSTOMER_FIELDS + ["password"], row))
    stored_password = data.pop("password")

    if not verify_password(password, stored_password):
        return None

    if conn is not None:
        upgrade_password_if_needed(
            cursor,
            conn,
            table="master.customers",
            id_column="user_id",
            id_value=user_id,
            plain_password=password,
            stored_password=stored_password,
        )

    return data


def change_customer_password(
    cursor,
    conn,
    *,
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> Tuple[bool, str]:
    """
    Change a customer password after verifying the current password.

    Returns (True, success_key) or (False, error_key) for UI messaging.
    """
    user_id = (user_id or "").strip()
    current_password = (current_password or "").strip()
    new_password = (new_password or "").strip()
    confirm_password = (confirm_password or "").strip()

    if not user_id or not current_password or not new_password or not confirm_password:
        return False, "password_change_missing_fields"
    if new_password != confirm_password:
        return False, "password_change_mismatch"
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, "password_change_too_short"
    if new_password == current_password:
        return False, "password_change_same_as_current"

    cursor.execute(
        """
        SELECT user_id, password
        FROM master.customers
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return False, "password_change_customer_not_found"

    resolved_id, stored_password = row[0], row[1]
    if not verify_password(current_password, stored_password):
        return False, "password_change_wrong_current"

    cursor.execute(
        """
        UPDATE master.customers
        SET password = %s
        WHERE user_id = %s
        """,
        (hash_password(new_password), resolved_id),
    )
    conn.commit()
    return True, "password_change_success"


def reset_customer_password(
    cursor,
    conn,
    *,
    user_id: str,
    email: str,
    new_password: str,
    confirm_password: str,
) -> Tuple[bool, str]:
    """
    Reset password when the customer forgot it.

    Verifies user_id + email on file (no current password required).
    Returns (True, success_key) or (False, error_key).
    """
    user_id = (user_id or "").strip()
    email = (email or "").strip().lower()
    new_password = (new_password or "").strip()
    confirm_password = (confirm_password or "").strip()

    if not user_id or not email or not new_password or not confirm_password:
        return False, "password_change_missing_fields"
    if new_password != confirm_password:
        return False, "password_change_mismatch"
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, "password_change_too_short"

    cursor.execute(
        """
        SELECT user_id, email, password
        FROM master.customers
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return False, "password_change_customer_not_found"

    resolved_id, stored_email, stored_password = row[0], (row[1] or "").strip().lower(), row[2]
    if not stored_email or stored_email != email:
        return False, "password_reset_email_mismatch"

    if verify_password(new_password, stored_password):
        return False, "password_change_same_as_current"

    cursor.execute(
        """
        UPDATE master.customers
        SET password = %s
        WHERE user_id = %s
        """,
        (hash_password(new_password), resolved_id),
    )
    conn.commit()
    return True, "password_reset_success"
