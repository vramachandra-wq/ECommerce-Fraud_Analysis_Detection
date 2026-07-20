from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_batch
from config import DB_CONFIG

router = APIRouter()

# --- PYDANTIC MODELS ---

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


# --- ENDPOINTS ---

@router.post("/create-order")
def create_order(data: CreateOrderRequest):
    try:
        # Using 'with' automatically handles conn.commit() on success 
        # and conn.rollback() & conn.close() on failure/exit.
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                
                # 1. Insert the main order record
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
                        data.order_approved_at, data.order_rejected_at
                    ),
                )

                # 2. Insert rule hits efficiently using batch processing
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
                        rules_data
                    )

        return {"message": "Order Created successfully"}

    except Exception as e:
        # If the database fails, return a 500 error so Streamlit knows it failed
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")