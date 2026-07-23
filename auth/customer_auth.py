from typing import Optional, Dict, Any

from auth.passwords import upgrade_password_if_needed, verify_password

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
