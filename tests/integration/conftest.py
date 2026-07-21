"""Fixtures for integration / E2E tests against live PostgreSQL."""

import uuid
from datetime import datetime, timedelta

import psycopg2
import pytest
from fastapi.testclient import TestClient

from config import DB_CONFIG
from fraud_engine.engine import clear_metadata_cache
from fraud_engine.rules import clear_interval_cache


def _can_connect() -> bool:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_available():
    if not _can_connect():
        pytest.skip(
            "PostgreSQL is not reachable. Start it with `.\\start.ps1` or "
            "`podman compose up -d`, then re-run with: pytest -m integration"
        )


@pytest.fixture
def db_conn(db_available):
    """Real DB connection; rolls back leftover work and always closes."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def db_cursor(db_conn):
    cur = db_conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


@pytest.fixture
def api_client(db_available):
    """FastAPI TestClient hitting the real database (no psycopg2 mocks)."""
    from api.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def unique_suffix():
    return uuid.uuid4().hex[:8].upper()


@pytest.fixture
def test_order_id(unique_suffix):
    # master.orders.order_id is VARCHAR(20)
    return f"E2E-{unique_suffix}"  # 12 chars


@pytest.fixture
def cleanup_orders(db_conn, db_cursor):
    """Track order_ids created during a test and delete them afterward."""
    created = []

    def register(order_id: str):
        created.append(order_id)
        return order_id

    yield register

    for order_id in created:
        db_cursor.execute(
            "DELETE FROM master.order_rule_hits WHERE order_id = %s",
            (order_id,),
        )
        db_cursor.execute(
            "DELETE FROM master.orders WHERE order_id = %s",
            (order_id,),
        )


@pytest.fixture
def cleanup_blacklist(db_conn, db_cursor):
    """Track blacklist rows created during a test and remove them afterward."""
    ips, phones, emails = [], [], []

    class Tracker:
        def ip(self, value: str):
            ips.append(value)
            return value

        def phone(self, value: str):
            phones.append(value)
            return value

        def email(self, value: str):
            emails.append(value)
            return value

    yield Tracker()

    for ip in ips:
        db_cursor.execute(
            "DELETE FROM master.ip_blacklist WHERE ip_address = %s",
            (ip,),
        )
    for phone in phones:
        db_cursor.execute(
            "DELETE FROM master.phone_blacklist WHERE phone_number = %s",
            (phone,),
        )
    for email in emails:
        db_cursor.execute(
            "DELETE FROM master.email_blacklist WHERE email = %s",
            (email,),
        )


@pytest.fixture
def clean_customer(db_cursor, unique_suffix):
    """Insert a throwaway customer with no order history (avoids seed velocity noise)."""
    from auth.passwords import hash_password

    user_id = f"E2U{unique_suffix[:5]}"  # fits VARCHAR(20)
    customer = {
        "user_id": user_id,
        "password": "e2e-pass-123",
        "program_id": "P1",
        "customer_name": "E2E Clean User",
        "email": f"clean-{unique_suffix.lower()}@e2e.test",
        "phone_number": f"80{unique_suffix[:8]}",
    }

    db_cursor.execute(
        """
        INSERT INTO master.customers (
            user_id, customer_name, email, phone_number, default_address,
            street, city, state, country, zip_code, program_id, password
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            customer["user_id"],
            customer["customer_name"],
            customer["email"],
            customer["phone_number"],
            "9 Clean Street, Chennai, TN 600001",
            "9 Clean Street",
            "Chennai",
            "TN",
            "India",
            "600001",
            customer["program_id"],
            hash_password(customer["password"]),
        ),
    )

    yield customer

    # Orders for this user must be gone first (cleanup_orders runs after yield
    # of that fixture only if used; delete any leftovers here too).
    db_cursor.execute(
        "SELECT order_id FROM master.orders WHERE user_id = %s",
        (user_id,),
    )
    for (order_id,) in db_cursor.fetchall():
        db_cursor.execute(
            "DELETE FROM master.order_rule_hits WHERE order_id = %s",
            (order_id,),
        )
        db_cursor.execute(
            "DELETE FROM master.orders WHERE order_id = %s",
            (order_id,),
        )
    db_cursor.execute(
        "DELETE FROM master.customers WHERE user_id = %s",
        (user_id,),
    )


@pytest.fixture
def clean_p2_customer(db_cursor, unique_suffix):
    """Throwaway P2 customer for R001 iPhone hold tests."""
    from auth.passwords import hash_password

    user_id = f"E2P{unique_suffix[:5]}"
    customer = {
        "user_id": user_id,
        "password": "e2e-pass-123",
        "program_id": "P2",
        "customer_name": "E2E P2 User",
        "email": f"p2-{unique_suffix.lower()}@e2e.test",
        "phone_number": f"81{unique_suffix[:8]}",
    }

    db_cursor.execute(
        """
        INSERT INTO master.customers (
            user_id, customer_name, email, phone_number, default_address,
            street, city, state, country, zip_code, program_id, password
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            customer["user_id"],
            customer["customer_name"],
            customer["email"],
            customer["phone_number"],
            "9 P2 Street, Chennai, TN 600001",
            "9 P2 Street",
            "Chennai",
            "TN",
            "India",
            "600001",
            customer["program_id"],
            hash_password(customer["password"]),
        ),
    )

    yield customer

    db_cursor.execute(
        "SELECT order_id FROM master.orders WHERE user_id = %s",
        (user_id,),
    )
    for (order_id,) in db_cursor.fetchall():
        db_cursor.execute(
            "DELETE FROM master.order_rule_hits WHERE order_id = %s",
            (order_id,),
        )
        db_cursor.execute(
            "DELETE FROM master.orders WHERE order_id = %s",
            (order_id,),
        )
    db_cursor.execute(
        "DELETE FROM master.customers WHERE user_id = %s",
        (user_id,),
    )


@pytest.fixture(autouse=True)
def _clear_fraud_caches():
    clear_metadata_cache()
    clear_interval_cache()
    yield
    clear_metadata_cache()
    clear_interval_cache()


# Seed credentials from init_scripts (passwords may be bcrypt-hashed in DB)
SEED_CUSTOMER = {
    "user_id": "U1001",
    "password": "password123",
    "program_id": "P1",
}
SEED_CUSTOMER_P2 = {
    "user_id": "U1002",
    "password": "password123",
    "program_id": "P2",
}
SEED_ANALYST = {
    "analyst_id": "A0",
    "username": "admin",
    "password": "admin123",
    "role": "Admin",
}

# Catalog rows known to exist in seed data
SEED_PRODUCT = {
    "product_id": "PROD-9986",
    "product_name": "Laptop Cooling Pad Max",
    "category": "Peripherals",
    "price": 3126.93,
}
SEED_IPHONE = {
    "product_id": "PROD-9901",
    "product_name": "iPhone 16 Pro Max",
    "category": "Electronics",
    "price": 145000.00,
}
SEED_DEVICE = "DEV-MOB-I16"


def build_order_payload(*, order_id: str, disposition: dict, customer: dict, product: dict, **overrides):
    now = datetime.now()
    is_fraud = disposition["is_fraud"]
    base = {
        "order_id": order_id,
        "user_id": customer["user_id"],
        "program_id": customer["program_id"],
        "product_id": product["product_id"],
        "category": product["category"],
        "product_name": product["product_name"],
        "quantity": 1,
        "amount": float(product["price"]),
        "ip_address": "10.20.30.40",
        "device_id": SEED_DEVICE,
        "customer_name": "E2E Tester",
        "email": f"e2e-{order_id.lower()}@example.com",
        "address": "1 Test Street, Chennai, TN 600001",
        "street": "1 Test Street",
        "city": "Chennai",
        "state": "TN",
        "country": "India",
        "zip_code": "600001",
        "phone_number": "9000000001",
        "order_timestamp": str(now),
        "delay_minutes": disposition["delay_minutes"],
        "is_fraud": is_fraud,
        "flagged_reason": disposition["flagged_reason"],
        "order_status": disposition["order_status"],
        "order_approved_at": None if is_fraud or disposition["order_status"] != "APPROVED" else str(now),
        "order_rejected_at": str(now) if is_fraud else None,
        "triggered_rules": disposition["triggered_rules"],
    }
    base.update(overrides)
    return base


def past_timestamp(minutes_ago: int = 200) -> datetime:
    return datetime.now() - timedelta(minutes=minutes_ago)
