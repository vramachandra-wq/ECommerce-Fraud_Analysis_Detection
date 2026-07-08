from fastapi import APIRouter, Request, HTTPException
import psycopg2
from config import DB_CONFIG

router = APIRouter()

@router.post("/create-order")
async def create_order(request: Request):
    data = await request.json()

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
                        data["order_id"], 
                        data["user_id"], 
                        data["program_id"], 
                        data["product_id"], 
                        data["category"], 
                        data["product_name"], 
                        data["quantity"], 
                        data["amount"], 
                        data["ip_address"], 
                        data["device_id"], 
                        data["customer_name"], 
                        data["email"], 
                        data["address"], 
                        data.get("street"), 
                        data.get("city"), 
                        data.get("state"), 
                        data.get("country", "India"), 
                        data.get("zip_code"),
                        data["phone_number"], 
                        data["order_timestamp"],
                        data["delay_minutes"], 
                        data["is_fraud"], 
                        data["flagged_reason"], 
                        data["order_status"], 
                        data["order_approved_at"], 
                        data["order_rejected_at"]
                    ),
                )

                # 2. Insert rule hits (if any exist)
                # Using .get() safely handles cases where triggered_rules might be empty
                for rule in data.get("triggered_rules", []):
                    cur.execute(
                        """
                        INSERT INTO master.order_rule_hits
                        (order_id, rule_id, rule_name, rule_description)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (
                            data["order_id"],
                            rule["rule_id"],
                            rule["rule_name"],
                            rule["rule_description"],
                        ),
                    )

        return {"message": "Order Created successfully"}

    except Exception as e:
        # If the database fails, return a 500 error so Streamlit knows it failed
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")