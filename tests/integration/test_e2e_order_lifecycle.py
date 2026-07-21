"""
End-to-end integration tests against live PostgreSQL.

Prerequisites:
  - Postgres running (podman compose / .\\start.ps1)
  - .env configured with DB_* values

Run:
  .\\.venv\\Scripts\\python.exe -m pytest -m integration -q
  .\\.venv\\Scripts\\python.exe -m pytest -m \"not integration\" -q   # unit only
"""

from datetime import datetime

import pytest

from auth.analyst_auth import authenticate_analyst
from auth.customer_auth import authenticate_customer
from fraud_engine.auto_approval import sync_expired_holds
from fraud_engine.engine import evaluate_order

from tests.integration.conftest import (
    SEED_ANALYST,
    SEED_CUSTOMER,
    SEED_DEVICE,
    SEED_IPHONE,
    SEED_PRODUCT,
    build_order_payload,
)


pytestmark = pytest.mark.integration


def _order_ctx(customer, product, **overrides):
    ctx = {
        "user_id": customer["user_id"],
        "program_id": customer["program_id"],
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "category": product["category"],
        "quantity": 1,
        "amount": float(product["price"]),
        "ip_address": "10.20.30.40",
        "device_id": SEED_DEVICE,
        "email": customer.get("email", f"safe-{customer['user_id'].lower()}@example.com"),
        "phone_number": customer.get("phone_number", "9000000001"),
        "address": f"E2E Address {customer['user_id']}, Chennai, TN 600001",
        "order_timestamp": datetime.now(),
    }
    ctx.update(overrides)
    return ctx


# ---------- auth against real DB ----------

def test_customer_login_against_db(db_cursor):
    customer = authenticate_customer(
        db_cursor,
        SEED_CUSTOMER["user_id"],
        SEED_CUSTOMER["password"],
        conn=db_cursor.connection,
    )
    assert customer is not None
    assert customer["user_id"] == SEED_CUSTOMER["user_id"]
    assert "password" not in customer


def test_analyst_login_against_db(db_cursor):
    analyst = authenticate_analyst(
        db_cursor,
        SEED_ANALYST["username"],
        SEED_ANALYST["password"],
        conn=db_cursor.connection,
    )
    assert analyst is not None
    assert analyst["role"] == "Admin"


# ---------- full lifecycle: evaluate -> API persist -> DB verify ----------

def test_e2e_approved_order_flow(
    api_client, db_cursor, test_order_id, cleanup_orders, clean_customer
):
    cleanup_orders(test_order_id)

    disposition = evaluate_order(db_cursor, _order_ctx(clean_customer, SEED_PRODUCT))
    assert disposition["order_status"] == "APPROVED", disposition
    assert disposition["is_fraud"] is False

    payload = build_order_payload(
        order_id=test_order_id,
        disposition=disposition,
        customer=clean_customer,
        product=SEED_PRODUCT,
        email=clean_customer["email"],
        phone_number=clean_customer["phone_number"],
        customer_name=clean_customer["customer_name"],
    )
    response = api_client.post("/create-order", json=payload)
    assert response.status_code == 200, response.text

    db_cursor.execute(
        "SELECT order_status, is_fraud FROM master.orders WHERE order_id = %s",
        (test_order_id,),
    )
    row = db_cursor.fetchone()
    assert row is not None
    assert row[0] == "APPROVED"
    assert row[1] is False


def test_e2e_p2_iphone_hold_then_approve(
    api_client, db_cursor, test_order_id, cleanup_orders, clean_p2_customer
):
    cleanup_orders(test_order_id)

    disposition = evaluate_order(
        db_cursor,
        _order_ctx(clean_p2_customer, SEED_IPHONE),
    )
    assert disposition["order_status"] == "ON_HOLD", disposition
    assert disposition["delay_minutes"] > 0
    assert any(r["rule_id"] == "R001" for r in disposition["triggered_rules"])

    payload = build_order_payload(
        order_id=test_order_id,
        disposition=disposition,
        customer=clean_p2_customer,
        product=SEED_IPHONE,
        email=clean_p2_customer["email"],
        phone_number=clean_p2_customer["phone_number"],
        customer_name=clean_p2_customer["customer_name"],
    )
    response = api_client.post("/create-order", json=payload)
    assert response.status_code == 200, response.text

    pending = api_client.get("/pending-reviews")
    assert pending.status_code == 200
    order_ids = [o["order_id"] for o in pending.json()["data"]]
    assert test_order_id in order_ids

    approve = api_client.put(
        "/approve-order",
        json={
            "order_id": test_order_id,
            "approved_at": str(datetime.now()),
            "reviewed_by": SEED_ANALYST["analyst_id"],
            "review_comments": "E2E approve after hold",
        },
    )
    assert approve.status_code == 200, approve.text

    db_cursor.execute(
        "SELECT order_status, is_fraud, reviewed_by FROM master.orders WHERE order_id = %s",
        (test_order_id,),
    )
    status, is_fraud, reviewed_by = db_cursor.fetchone()
    assert status == "APPROVED"
    assert is_fraud is False
    assert reviewed_by == SEED_ANALYST["analyst_id"]


def test_e2e_blacklisted_ip_rejects(
    api_client,
    db_cursor,
    test_order_id,
    cleanup_orders,
    cleanup_blacklist,
    unique_suffix,
    clean_customer,
):
    cleanup_orders(test_order_id)
    bad_ip = cleanup_blacklist.ip(f"203.0.113.{int(unique_suffix[:2], 16) % 200 + 1}")

    db_cursor.execute(
        """
        INSERT INTO master.ip_blacklist (ip_address, reason, blacklisted_by, is_active)
        VALUES (%s, %s, %s, TRUE)
        """,
        (bad_ip, "E2E test blacklist", SEED_ANALYST["analyst_id"]),
    )

    disposition = evaluate_order(
        db_cursor,
        _order_ctx(clean_customer, SEED_PRODUCT, ip_address=bad_ip),
    )
    assert disposition["order_status"] == "REJECTED", disposition
    assert disposition["is_fraud"] is True
    assert any(r["rule_id"] == "R007" for r in disposition["triggered_rules"])

    payload = build_order_payload(
        order_id=test_order_id,
        disposition=disposition,
        customer=clean_customer,
        product=SEED_PRODUCT,
        ip_address=bad_ip,
        email=clean_customer["email"],
        phone_number=clean_customer["phone_number"],
        customer_name=clean_customer["customer_name"],
    )
    response = api_client.post("/create-order", json=payload)
    assert response.status_code == 200, response.text

    db_cursor.execute(
        "SELECT order_status, is_fraud FROM master.orders WHERE order_id = %s",
        (test_order_id,),
    )
    status, is_fraud = db_cursor.fetchone()
    assert status == "REJECTED"
    assert is_fraud is True

    db_cursor.execute(
        "SELECT COUNT(*) FROM master.order_rule_hits WHERE order_id = %s AND rule_id = 'R007'",
        (test_order_id,),
    )
    assert db_cursor.fetchone()[0] == 1


def test_e2e_reject_pending_review_order(
    api_client, db_cursor, test_order_id, cleanup_orders, clean_p2_customer
):
    cleanup_orders(test_order_id)

    disposition = evaluate_order(
        db_cursor,
        _order_ctx(clean_p2_customer, SEED_IPHONE),
    )
    disposition = {
        **disposition,
        "order_status": "PENDING_REVIEW",
        "delay_minutes": 0,
        "is_fraud": False,
    }

    payload = build_order_payload(
        order_id=test_order_id,
        disposition=disposition,
        customer=clean_p2_customer,
        product=SEED_IPHONE,
        email=clean_p2_customer["email"],
        phone_number=clean_p2_customer["phone_number"],
        customer_name=clean_p2_customer["customer_name"],
    )
    assert api_client.post("/create-order", json=payload).status_code == 200

    reject = api_client.put(
        "/reject-order",
        json={
            "order_id": test_order_id,
            "rejected_at": str(datetime.now()),
            "reviewed_by": SEED_ANALYST["analyst_id"],
            "review_comments": "E2E reject",
            "is_fraud": True,
        },
    )
    assert reject.status_code == 200, reject.text

    db_cursor.execute(
        "SELECT order_status, is_fraud FROM master.orders WHERE order_id = %s",
        (test_order_id,),
    )
    status, is_fraud = db_cursor.fetchone()
    assert status == "REJECTED"
    assert is_fraud is True


def test_e2e_auto_approval_of_expired_hold(
    db_conn, db_cursor, test_order_id, cleanup_orders, clean_customer
):
    cleanup_orders(test_order_id)

    db_cursor.execute(
        """
        INSERT INTO master.orders (
            order_id, user_id, program_id, product_id, category, product_name,
            quantity, amount, ip_address, device_id, customer_name, email, address,
            phone_number, order_timestamp, delay_minutes, is_fraud, flagged_reason,
            order_status
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            1, %s, %s, %s, %s, %s, %s,
            %s, NOW() - INTERVAL '200 minutes', %s, FALSE, %s,
            'ON_HOLD'
        )
        """,
        (
            test_order_id,
            clean_customer["user_id"],
            clean_customer["program_id"],
            SEED_PRODUCT["product_id"],
            SEED_PRODUCT["category"],
            SEED_PRODUCT["product_name"],
            float(SEED_PRODUCT["price"]),
            "10.20.30.41",
            SEED_DEVICE,
            clean_customer["customer_name"],
            clean_customer["email"],
            "1 Hold Street",
            clean_customer["phone_number"],
            180,
            "R001: E2E expired hold",
        ),
    )

    updated = sync_expired_holds(db_conn, db_cursor)
    assert updated >= 1

    db_cursor.execute(
        "SELECT order_status, is_fraud, order_approved_at FROM master.orders WHERE order_id = %s",
        (test_order_id,),
    )
    status, is_fraud, approved_at = db_cursor.fetchone()
    assert status == "APPROVED"
    assert is_fraud is False
    assert approved_at is not None


def test_e2e_admin_blacklist_phone_via_api(
    api_client, db_cursor, cleanup_blacklist, unique_suffix
):
    phone = cleanup_blacklist.phone(f"91{unique_suffix[:8]}")

    response = api_client.post(
        "/blacklist-phone",
        json={
            "phone_number": phone,
            "reason": "E2E phone blacklist",
            "blacklisted_by": SEED_ANALYST["analyst_id"],
        },
    )
    assert response.status_code == 200, response.text

    db_cursor.execute(
        """
        SELECT is_active, reason FROM master.phone_blacklist
        WHERE phone_number = %s
        """,
        (phone,),
    )
    row = db_cursor.fetchone()
    assert row is not None
    assert row[0] is True
    assert row[1] == "E2E phone blacklist"
