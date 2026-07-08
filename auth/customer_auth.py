"""Customer login for the Customer Portal.

NOTE: master.customers.password is a plain VARCHAR with plaintext seed
values, per the given schema. This demo app compares passwords directly
against that column. Do not reuse this pattern for real credentials -
in production, add a hashed-password column and verify with e.g. bcrypt.
"""

CUSTOMER_FIELDS = [
    "user_id", "customer_name", "email", "phone_number",
    "default_address", "program_id",
]


def authenticate_customer(cursor, user_id: str, password: str):
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
