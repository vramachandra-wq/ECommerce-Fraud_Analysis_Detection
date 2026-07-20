"""Order ID generation and pricing helpers."""


def generate_order_id(cursor) -> str:
    """ORD-000001, ORD-000002, ... via a dedicated Postgres sequence."""
    cursor.execute("SELECT nextval('master.order_id_seq')")
    seq = cursor.fetchone()[0]
    return f"ORD-{seq:06d}"


def calculate_total(price, quantity) -> float:
    return round(float(price) * int(quantity), 2)
