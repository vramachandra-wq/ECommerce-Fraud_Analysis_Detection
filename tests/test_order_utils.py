from unittest.mock import MagicMock

from utils.order_utils import calculate_total, generate_order_id


def test_calculate_total():
    assert calculate_total(100, 2) == 200.0


def test_calculate_total_decimal_price():
    assert calculate_total(99.99, 3) == 299.97


def test_calculate_total_single_quantity():
    assert calculate_total(250, 1) == 250.0


def test_generate_order_id():
    cursor = MagicMock()
    cursor.fetchone.return_value = [1]

    order_id = generate_order_id(cursor)

    cursor.execute.assert_called_once_with(
        "SELECT nextval('master.order_id_seq')"
    )
    assert order_id == "ORD-000001"