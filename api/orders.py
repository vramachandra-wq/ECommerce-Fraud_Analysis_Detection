from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import execute_batch
import psycopg2

from api.auth import get_current_session
from config import DB_CONFIG
from utils.system_audit import actor_from_session, log_system_event

router = APIRouter()


class RuleHit(BaseModel):
    rule_id: str
    rule_name: str
    rule_description: str


class CreateOrderRequest(BaseModel):
    order_id: str
    user_id: str
    program_id: str
    product_id: str
    category: str
    product_name: str
    quantity: int
    amount: float
    ip_address: str
    device_id: str
    customer_name: str
    email: str
    address: str
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    zip_code: Optional[str] = None
    phone_number: str
    order_timestamp: str
    delay_minutes: int
    is_fraud: bool
    flagged_reason: Optional[str] = None
    order_status: str
    order_approved_at: Optional[str] = None
    order_rejected_at: Optional[str] = None
    triggered_rules: List[RuleHit] = Field(default_factory=list)


@router.post("/create-order")
def create_order(
    data: CreateOrderRequest,
    session: Dict[str, Any] = Depends(get_current_session),
):
    """Internal/analyst-authenticated order insert (pre-evaluated). Customer checkout uses /shop/orders."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
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
                        data.order_id, data.user_id, data.program_id, data.product_id, data.category,
                        data.product_name, data.quantity, data.amount, data.ip_address, data.device_id,
                        data.customer_name, data.email, data.address,
                        data.street, data.city, data.state, data.country, data.zip_code,
                        data.phone_number, data.order_timestamp,
                        data.delay_minutes, data.is_fraud, data.flagged_reason, data.order_status,
                        data.order_approved_at, data.order_rejected_at,
                    ),
                )

                if data.triggered_rules:
                    rules_data = [
                        (data.order_id, rule.rule_id, rule.rule_name, rule.rule_description)
                        for rule in data.triggered_rules
                    ]
                    execute_batch(
                        cur,
                        """
                        INSERT INTO master.order_rule_hits
                        (order_id, rule_id, rule_name, rule_description)
                        VALUES (%s,%s,%s,%s)
                        """,
                        rules_data,
                    )

                log_system_event(
                    cur,
                    action="ORDER_CREATE",
                    **actor_from_session(session),
                    resource_type="order",
                    resource_id=data.order_id,
                    details={
                        "status": data.order_status,
                        "amount": data.amount,
                        "via": "create-order",
                        "rules": [r.rule_id for r in data.triggered_rules],
                    },
                    request_path="/create-order",
                )

        return {"message": "Order Created successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
