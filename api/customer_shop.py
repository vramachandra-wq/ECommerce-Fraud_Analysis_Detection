"""Customer shop API — login, catalogs, and place-order (fraud evaluate + persist)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg2
from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
from database.order_items import (
    ensure_order_items_table,
    fetch_order_items,
    header_summary,
    insert_order_items,
)
from ui.i18n import TRANSLATIONS
from fraud_engine.engine import evaluate_order_with_items
from notifications.rejection import notify_order_rejected
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


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class PlaceOrderRequest(BaseModel):
    """Place one customer order.

    Preferred: ``items`` with one or more products.
    Legacy (still supported): single ``product_id`` + ``quantity``.
    """

    items: Optional[List[CartItemIn]] = None
    product_id: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=1)
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


def _resolve_cart_items(body: PlaceOrderRequest) -> List[CartItemIn]:
    """Prefer items[]; fall back to legacy product_id + quantity. Merge duplicate SKUs."""
    raw: List[CartItemIn] = list(body.items or [])
    if not raw:
        if body.product_id and body.quantity:
            raw = [CartItemIn(product_id=body.product_id, quantity=body.quantity)]
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide items[{product_id, quantity}, ...] or product_id + quantity",
            )

    merged: Dict[str, int] = {}
    for item in raw:
        pid = (item.product_id or "").strip()
        if not pid:
            raise HTTPException(status_code=400, detail="Each item needs a product_id")
        merged[pid] = merged.get(pid, 0) + int(item.quantity)

    return [CartItemIn(product_id=pid, quantity=qty) for pid, qty in merged.items()]


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
    cart_items = _resolve_cart_items(body)

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
                ensure_order_items_table(cur)

                # Resolve every cart line against master.products
                lines: List[Dict[str, Any]] = []
                for item in cart_items:
                    cur.execute(
                        """
                        SELECT product_id, product_name, category, price
                        FROM master.products
                        WHERE product_id = %s
                        """,
                        (item.product_id,),
                    )
                    prow = cur.fetchone()
                    if not prow:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid product: {item.product_id}",
                        )
                    product_id, product_name, category, price = prow
                    qty = int(item.quantity)
                    lines.append(
                        {
                            "product_id": product_id,
                            "product_name": product_name,
                            "category": category,
                            "quantity": qty,
                            "unit_price": float(price),
                            "line_amount": calculate_total(price, qty),
                        }
                    )

                summary = header_summary(lines)
                product_id = summary["product_id"]
                product_name = summary["product_name"]
                category = summary["category"]
                quantity = summary["quantity"]
                amount = summary["amount"]

                order_id = generate_order_id(cur)
                # Per-item product rules + once-per-order velocity/blacklist, then roll up.
                base_ctx = {
                    "user_id": customer["user_id"],
                    "program_id": body.program_id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category,
                    "quantity": int(quantity),
                    "amount": amount,
                    "ip_address": ip_address,
                    "device_id": body.device_id,
                    "email": email,
                    "phone_number": customer["phone_number"],
                    "address": formatted_address,
                    "order_timestamp": order_timestamp,
                }
                disposition = evaluate_order_with_items(cur, base_ctx, lines)
                status = disposition["order_status"]
                order_approved_at = order_timestamp if status == "APPROVED" else None
                order_rejected_at = order_timestamp if status == "REJECTED" else None

                # Persist per-line rule outcomes onto order_items rows.
                by_product = {
                    str(ir.get("product_id")): ir
                    for ir in (disposition.get("item_results") or [])
                }
                for line in lines:
                    ir = by_product.get(str(line.get("product_id"))) or {}
                    line["line_status"] = ir.get("order_status") or status
                    line["flagged_reason"] = ir.get("flagged_reason")

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
                        int(quantity),
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

                insert_order_items(cur, order_id, lines)

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
                        "item_count": len(lines),
                        "via": "shop",
                        "rules": [r.get("rule_id") for r in rules],
                        "item_rule_status": [
                            {
                                "product_id": ir.get("product_id"),
                                "order_status": ir.get("order_status"),
                                "rules": [r.get("rule_id") for r in (ir.get("triggered_rules") or [])],
                            }
                            for ir in (disposition.get("item_results") or [])
                        ],
                    },
                    request_path="/shop/orders",
                )
                saved_items = fetch_order_items(cur, order_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Order failed. Please try again.") from exc

    if status == "REJECTED":
        try:
            notify_order_rejected(order_id)
        except Exception:
            pass

    return {
        "message": "Order created successfully",
        "order_id": order_id,
        "order_status": status,
        "amount": amount,
        "product_name": product_name,
        "quantity": int(quantity),
        "item_count": len(saved_items),
        "items": saved_items,
        "flagged_reason": disposition.get("flagged_reason"),
        "item_results": disposition.get("item_results") or [],
    }


def _serialize_shop_order_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize DB order fields for the customer shop JSON API."""
    out = dict(row)
    out["amount"] = float(out["amount"]) if out.get("amount") is not None else 0.0
    out["quantity"] = int(out.get("quantity") or 0)
    out["item_count"] = int(out.get("item_count") or 0)
    if out.get("order_timestamp") is not None and hasattr(out["order_timestamp"], "isoformat"):
        out["order_timestamp"] = out["order_timestamp"].isoformat()
    return out


def _format_delivery_address(order: Dict[str, Any]) -> str:
    """Build a single-line delivery address from order fields."""
    parts = [
        str(order.get("street") or "").strip(),
        str(order.get("city") or "").strip(),
        str(order.get("state") or "").strip(),
        str(order.get("zip_code") or "").strip(),
        str(order.get("country") or "").strip(),
    ]
    composed = ", ".join(p for p in parts if p)
    if composed:
        return composed
    return str(order.get("address") or "").strip()


@router.get("/shop/orders")
def shop_list_orders(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    customer: Dict[str, Any] = Depends(get_current_customer),
):
    """Order history for the signed-in customer (newest first)."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ensure_order_items_table(cur)
                cur.execute(
                    """
                    SELECT COUNT(*) FROM master.orders WHERE user_id = %s
                    """,
                    (customer["user_id"],),
                )
                total = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                        o.order_id,
                        o.product_id,
                        o.product_name,
                        o.category,
                        o.quantity,
                        o.amount,
                        o.order_status,
                        o.order_timestamp,
                        COALESCE(oi.item_count, 0) AS item_count
                    FROM master.orders o
                    LEFT JOIN (
                        SELECT order_id, COUNT(*)::int AS item_count
                        FROM master.order_items
                        GROUP BY order_id
                    ) oi ON oi.order_id = o.order_id
                    WHERE o.user_id = %s
                    ORDER BY o.order_timestamp DESC NULLS LAST, o.order_id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (customer["user_id"], limit, offset),
                )
                cols = [
                    "order_id",
                    "product_id",
                    "product_name",
                    "category",
                    "quantity",
                    "amount",
                    "order_status",
                    "order_timestamp",
                    "item_count",
                ]
                orders = [
                    _serialize_shop_order_row(dict(zip(cols, row)))
                    for row in cur.fetchall()
                ]
                # Older single-SKU rows may have no order_items yet.
                for order in orders:
                    if order["item_count"] <= 0 and order.get("product_id"):
                        order["item_count"] = 1
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load orders.") from exc

    return {
        "orders": orders,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/shop/orders/{order_id}")
def shop_get_order(
    order_id: str,
    customer: Dict[str, Any] = Depends(get_current_customer),
):
    """Fetch one of the current customer's orders including line items (Step A verify)."""
    oid = (order_id or "").strip()
    if not oid:
        raise HTTPException(status_code=400, detail="order_id required")

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                ensure_order_items_table(cur)
                cur.execute(
                    """
                    SELECT order_id, user_id, product_id, product_name, category,
                           quantity, amount, order_status, flagged_reason, order_timestamp,
                           street, city, state, zip_code, country, address
                    FROM master.orders
                    WHERE order_id = %s
                    """,
                    (oid,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Order not found")
                cols = [
                    "order_id",
                    "user_id",
                    "product_id",
                    "product_name",
                    "category",
                    "quantity",
                    "amount",
                    "order_status",
                    "flagged_reason",
                    "order_timestamp",
                    "street",
                    "city",
                    "state",
                    "zip_code",
                    "country",
                    "address",
                ]
                order = dict(zip(cols, row))
                if order["user_id"] != customer["user_id"]:
                    raise HTTPException(status_code=404, detail="Order not found")
                order = _serialize_shop_order_row(order)
                order["delivery_address"] = _format_delivery_address(order)
                items = fetch_order_items(cur, oid)
                # Backfill: older single-product orders may have no order_items rows yet.
                if not items and order.get("product_id"):
                    items = [
                        {
                            "order_item_id": None,
                            "line_no": 1,
                            "product_id": order["product_id"],
                            "product_name": order["product_name"],
                            "category": order["category"],
                            "quantity": order["quantity"],
                            "unit_price": (
                                round(order["amount"] / order["quantity"], 2)
                                if order["quantity"]
                                else order["amount"]
                            ),
                            "line_amount": order["amount"],
                        }
                    ]
                order["items"] = items
                order["item_count"] = len(items)
                return order
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load order.") from exc
