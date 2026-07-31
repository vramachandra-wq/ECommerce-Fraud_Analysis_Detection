"""Unit tests for multi-item order helpers (Step A)."""

from database.order_items import header_summary


def test_header_summary_single_item():
    lines = [
        {
            "product_id": "P1",
            "product_name": "iPhone 16",
            "category": "Phone",
            "quantity": 2,
            "unit_price": 100.0,
            "line_amount": 200.0,
        }
    ]
    s = header_summary(lines)
    assert s["product_id"] == "P1"
    assert s["product_name"] == "iPhone 16"
    assert s["category"] == "Phone"
    assert s["quantity"] == 2
    assert s["amount"] == 200.0


def test_header_summary_multi_items():
    lines = [
        {
            "product_id": "P1",
            "product_name": "iPhone 16",
            "category": "Phone",
            "quantity": 1,
            "unit_price": 100.0,
            "line_amount": 100.0,
        },
        {
            "product_id": "P2",
            "product_name": "Galaxy S24",
            "category": "Phone",
            "quantity": 3,
            "unit_price": 50.0,
            "line_amount": 150.0,
        },
    ]
    s = header_summary(lines)
    assert s["product_id"] == "P1"
    assert s["product_name"] == "iPhone 16 (+1 more)"
    assert s["category"] == "Phone"
    assert s["quantity"] == 4
    assert s["amount"] == 250.0


def test_header_summary_mixed_category():
    lines = [
        {
            "product_id": "P1",
            "product_name": "iPhone 16",
            "category": "Phone",
            "quantity": 1,
            "unit_price": 10.0,
            "line_amount": 10.0,
        },
        {
            "product_id": "P2",
            "product_name": "Earbuds",
            "category": "Audio",
            "quantity": 1,
            "unit_price": 5.0,
            "line_amount": 5.0,
        },
    ]
    s = header_summary(lines)
    assert s["category"] == "MULTI"
    assert s["amount"] == 15.0
