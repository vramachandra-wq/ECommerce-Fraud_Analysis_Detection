from typing import Optional, Dict, Any

CUSTOMER_FIELDS = [
    "user_id", "customer_name", "email", "phone_number",
    "default_address", "program_id",
]

def authenticate_customer(cursor, user_id: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Validates customer credentials against the database.
    Returns a dictionary of customer details if successful, otherwise None.
    """
    cursor.execute(
        """
        SELECT user_id, customer_name, email, phone_number, default_address, program_id
        FROM master.customers
        WHERE user_id = %s AND password = %s
        """,
        (user_id, password),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return dict(zip(CUSTOMER_FIELDS, row))