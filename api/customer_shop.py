"""Customer shop API — login, catalogs, and place-order (fraud evaluate + persist)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg2
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import execute_batch

from api.auth import create_session_token, verify_session_token
from auth.customer_auth import (
    CUSTOMER_FIELDS,
    authenticate_customer,
    change_customer_password,
    reset_customer_password,
)
from config import DB_CONFIG
from ui.i18n import TRANSLATIONS
from fraud_engine.engine import evaluate_order
from utils.order_utils import calculate_total, generate_order_id
from utils.queries import list_devices, list_products, list_programs
from utils.time_utils import utcnow_naive
from utils.system_audit import actor_from_customer, log_system_event

router = APIRouter()


class CustomerLoginRequest(BaseModel):
    user_id: str
    password: str


class ChangePasswordRequest(BaseModel):
    user_id: str = ""
    current_password: str
    new_password: str
    confirm_password: str


class ResetPasswordRequest(BaseModel):
    user_id: str
    email: str
    new_password: str
    confirm_password: str


class PlaceOrderRequest(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    program_id: str
    device_id: str
    ip_address: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "India"


def _message_for_key(key: str) -> str:
    entry = TRANSLATIONS.get(key) or {}
    return entry.get("en") or key


def _customer_token(user_id: str) -> str:
    # Reuse analyst token machinery with a customer-scoped subject.
    return create_session_token(f"customer:{user_id}")


def _user_id_from_token(token: str) -> Optional[str]:
    sub = verify_session_token(token)
    if not sub or not str(sub).startswith("customer:"):
        return None
    return str(sub).split(":", 1)[1]


def _fetch_customer(user_id: str) -> Optional[Dict[str, Any]]:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {", ".join(CUSTOMER_FIELDS)}
                FROM master.customers
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip(CUSTOMER_FIELDS, row))


def get_current_customer(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = _user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    customer = _fetch_customer(user_id)
    if not customer:
        raise HTTPException(status_code=401, detail="Customer not found")
    return customer


@router.post("/shop/auth/login")
def shop_login(body: CustomerLoginRequest):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            customer = authenticate_customer(
                cur, body.user_id.strip(), body.password, conn=conn
            )
    if not customer:
        log_system_event(
            action="AUTH_LOGIN",
            actor_type="customer",
            actor_id=body.user_id.strip(),
            outcome="failure",
            details={"reason": "invalid_credentials"},
            request_path="/shop/auth/login",
        )
        raise HTTPException(status_code=401, detail="Invalid user ID or password")
    log_system_event(
        action="AUTH_LOGIN",
        **actor_from_customer(customer),
        outcome="success",
        request_path="/shop/auth/login",
    )
    return {
        "customer": customer,
        "token": _customer_token(customer["user_id"]),
    }


@router.get("/shop/auth/me")
def shop_me(customer: Dict[str, Any] = Depends(get_current_customer)):
    return {"customer": customer}


@router.post("/shop/auth/change-password")
def shop_change_password(
    body: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
):
    """Change password from login screen (user_id required) or while logged in."""
    user_id = (body.user_id or "").strip()
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        token_user = _user_id_from_token(token)
        if token_user:
            user_id = token_user

    if not user_id:
        raise HTTPException(status_code=400, detail=_message_for_key("password_change_missing_fields"))

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            ok, message_key = change_customer_password(
                cur,
                conn,
                user_id=user_id,
                current_password=body.current_password,
                new_password=body.new_password,
                confirm_password=body.confirm_password,
            )

    if not ok:
        status = 404 if message_key == "password_change_customer_not_found" else 400
        raise HTTPException(status_code=status, detail=_message_for_key(message_key))

    return {
        "message": _message_for_key("password_change_success"),
        "message_key": "password_change_success",
    }


@router.post("/shop/auth/reset-password")
def shop_reset_password(body: ResetPasswordRequest):
    """Forgot-password reset: user_id + registered email + new password."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            ok, message_key = reset_customer_password(
                cur,
                conn,
                user_id=body.user_id,
                email=body.email,
                new_password=body.new_password,
                confirm_password=body.confirm_password,
            )

    if not ok:
        status = 404 if message_key == "password_change_customer_not_found" else 400
        raise HTTPException(status_code=status, detail=_message_for_key(message_key))

    return {
        "message": _message_for_key(message_key),
        "message_key": message_key,
    }


@router.get("/shop/catalog")
def shop_catalog(_customer: Dict[str, Any] = Depends(get_current_customer)):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            products = [
                {
                    "product_id": pid,
                    "product_name": name,
                    "category": cat,
                    "price": float(price),
                }
                for pid, name, cat, price in list_products(cur)
            ]
            programs = [
                {"program_id": pid, "program_name": name}
                for pid, name in list_programs(cur)
            ]
            devices = [
                {
                    "device_id": did,
                    "device_name": name,
                    "device_type": dtype,
                }
                for did, name, dtype in list_devices(cur)
            ]
    return {"products": products, "programs": programs, "devices": devices}


@router.post("/shop/orders")
def shop_place_order(
    body: PlaceOrderRequest,
    customer: Dict[str, Any] = Depends(get_current_customer),
):
    street = body.street.strip()
    city = body.city.strip()
    state = body.state.strip()
    zip_code = body.zip_code.strip()
    country = (body.country or "India").strip() or "India"
    ip_address = body.ip_address.strip()

    if not street or not city or not state or not zip_code:
        raise HTTPException(status_code=400, detail="Complete delivery address is required")
    if not ip_address:
        raise HTTPException(status_code=400, detail="IP address is required")
    if not (customer.get("phone_number") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="No phone number on file. Contact support before ordering.",
        )
    email = (customer.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required")

    formatted_address = f"{street}, {city}, {state} {zip_code}"
    order_timestamp = utcnow_naive()

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Resolve product
                cur.execute(
                    """
                    SELECT product_id, product_name, category, price
                    FROM master.products
                    WHERE product_id = %s
                    """,
                    (body.product_id,),
                )
                prow = cur.fetchone()
                if not prow:
                    raise HTTPException(status_code=400, detail="Invalid product")
                product_id, product_name, category, price = prow
                amount = calculate_total(price, body.quantity)

                order_id = generate_order_id(cur)
                ctx = {
                    "user_id": customer["user_id"],
                    "program_id": body.program_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "quantity": int(body.quantity),
                    "amount": amount,
                    "ip_address": ip_address,
                    "device_id": body.device_id,
                    "email": email,
                    "phone_number": customer["phone_number"],
                    "address": formatted_address,
                    "order_timestamp": order_timestamp,
                }
                disposition = evaluate_order(cur, ctx)
                status = disposition["order_status"]
                order_approved_at = order_timestamp if status == "APPROVED" else None
                order_rejected_at = order_timestamp if status == "REJECTED" else None

                cur.execute(
                    """
                    INSERT INTO master.orders (
                        order_id, user_id, program_id, product_id, category,
                        product_name, quantity, amount, ip_address, device_id,
                        customer_name, email, address,
                        street, city, state, country, zip_code,
                        phone_number, order_timestamp,
                        delay_minutes, is_fraud, flagged_reason, order_status,
                        order_approved_at, order_rejected_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s
                    )
                    """,
                    (
                        order_id,
                        customer["user_id"],
                        body.program_id,
                        product_id,
                        category,
                        product_name,
                        int(body.quantity),
                        amount,
                        ip_address,
                        body.device_id,
                        customer["customer_name"],
                        email,
                        formatted_address,
                        street,
                        city,
                        state,
                        country,
                        zip_code,
                        customer["phone_number"],
                        order_timestamp,
                        disposition["delay_minutes"],
                        disposition["is_fraud"],
                        disposition["flagged_reason"],
                        status,
                        order_approved_at,
                        order_rejected_at,
                    ),
                )

                rules: List[Dict[str, str]] = disposition.get("triggered_rules") or []
                if rules:
                    execute_batch(
                        cur,
                        """
                        INSERT INTO master.order_rule_hits
                        (order_id, rule_id, rule_name, rule_description)
                        VALUES (%s,%s,%s,%s)
                        """,
                        [
                            (
                                order_id,
                                r.get("rule_id"),
                                r.get("rule_name"),
                                r.get("rule_description"),
                            )
                            for r in rules
                        ],
                    )

                log_system_event(
                    cur,
                    action="ORDER_CREATE",
                    **actor_from_customer(customer),
                    resource_type="order",
                    resource_id=order_id,
                    details={
                        "status": status,
                        "amount": amount,
                        "via": "shop",
                        "rules": [r.get("rule_id") for r in rules],
                    },
                    request_path="/shop/orders",
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Order failed: {exc}") from exc

    return {
        "message": "Order created successfully",
        "order_id": order_id,
        "order_status": status,
        "amount": amount,
        "product_name": product_name,
        "quantity": int(body.quantity),
        "flagged_reason": disposition.get("flagged_reason"),
    }
