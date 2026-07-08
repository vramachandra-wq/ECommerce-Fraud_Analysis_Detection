import pandas as pd
import psycopg2
from psycopg2.extras import DictCursor
import random
from datetime import timedelta

# Assuming the fraud engine code provided is saved in a module named 'fraud_engine'
from fraud_engine.engine import evaluate_order

def process_orders_csv(input_csv_path: str, output_orders_path: str, output_rule_hits_path: str, db_connection_params: dict):
    """
    Reads a CSV of orders, evaluates them through the fraud engine, 
    and simulates manual review for 'On Hold' orders.
    """
    # 1. Read the input CSV into a pandas DataFrame
    df = pd.read_csv(input_csv_path)
    
    # 2. Convert date strings to datetime objects if necessary
    if 'order_timestamp' in df.columns:
        df['order_timestamp'] = pd.to_datetime(df['order_timestamp'])
    
    # 3. Connect to the database
    conn = psycopg2.connect(**db_connection_params)
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    # Prepare lists to store the main evaluation results
    statuses = []
    delays = []
    reasons = []
    is_fraud_flags = []
    approved_ats = []
    rejected_ats = []
    reviewed_bys = []
    
    rule_hits_data = []

    try:
        # 4a. Fetch rule metadata from the database (schema: master)
        rule_metadata = {}
        cursor.execute("SELECT rule_id, rule_name, rule_description FROM master.rule_master;")
        rules = cursor.fetchall()
        for rule in rules:
            rule_metadata[rule['rule_id']] = {
                "name": rule['rule_name'],
                "description": rule['rule_description']
            }
            
        # 4b. Fetch analyst users from the database (schema: master)
        cursor.execute("SELECT analyst_id FROM master.analyst_users;")
        analysts = [row['analyst_id'] for row in cursor.fetchall()]

        # 5. Iterate over the rows and evaluate each order
        for index, row in df.iterrows():
            order_id = row.get("order_id")
            order_ts = row.get("order_timestamp")
            
            ctx = {
                "order_id": order_id,
                "user_id": row.get("user_id"),
                "program_id": row.get("program_id"),
                "product_id": row.get("product_id"),
                "product_name": row.get("product_name"),
                "category": row.get("category"),
                "quantity": row.get("quantity"),
                "amount": row.get("amount"),
                "ip_address": row.get("ip_address"),
                "device_id": row.get("device_id"),
                "email": row.get("email"),
                "address": row.get("address"),
                "order_timestamp": order_ts
            }
            
            # Run the context through the fraud engine orchestrator
            result = evaluate_order(cursor, ctx)
            
            # Initialize simulated fields
            final_status = result["order_status"]
            triggered_rules = result.get("triggered_rules", [])
            app_at = None
            rej_at = None
            rev_by = None
            
            # Apply Manual Review / Timestamp Logic
            status_lower = final_status.lower()
            
            if status_lower == "approved":
                # Default system approval
                app_at = order_ts
                
            elif status_lower in ["on hold", "review pending", "pending", "review"]:
                # 10% chance to randomly reject manual reviews
                if random.random() < 0.10:
                    final_status = "Rejected"
                    random_minutes = random.randint(1, 180) # Up to 3 hours
                    if pd.notnull(order_ts):
                        rej_at = order_ts + timedelta(minutes=random_minutes)
                    rev_by = random.choice(analysts) if analysts else "System_Fallback"
                    
                else:
                    # For remaining On Hold, if R001 (iPhone rule) triggered -> Approve after 3 hours
                    if "R001" in triggered_rules:
                        final_status = "Approved"
                        if pd.notnull(order_ts):
                            app_at = order_ts + timedelta(hours=3)
                        rev_by = random.choice(analysts) if analysts else "System_Fallback"

            elif status_lower == "rejected":
                # System already rejected it (e.g., Blacklisted IP)
                if pd.notnull(order_ts):
                    rej_at = order_ts
                rev_by = None # Explicitly leave NULL for system actions
            
            # Store results for the main table
            statuses.append(final_status)
            delays.append(result["delay_minutes"])
            reasons.append(result["flagged_reason"])
            is_fraud_flags.append(result["is_fraud"])
            approved_ats.append(app_at)
            rejected_ats.append(rej_at)
            reviewed_bys.append(rev_by)
            
            # Process triggered rules to build the secondary order_rule_hit table
            for rule_id in triggered_rules:
                meta = rule_metadata.get(rule_id, {"name": "Unknown", "description": "No description available"})
                
                rule_hits_data.append({
                    "order_id": order_id,
                    "rule_id": rule_id,
                    "rule_name": meta["name"],
                    "rule_description": meta["description"],
                    "created_at": order_ts  # <--- Added created_at field mapped to order_ts
                })
                
    finally:
        cursor.close()
        conn.close()
        
    # 6. Append the results to the original DataFrame
    df['order_status'] = statuses
    df['delay_minutes'] = delays
    df['flagged_reason'] = reasons
    df['is_fraud'] = is_fraud_flags
    df['order_approved_at'] = approved_ats
    df['order_rejected_at'] = rejected_ats
    df['reviewed_by'] = reviewed_bys
    
    # 7. Create the order_rule_hit DataFrame
    # <--- Added created_at to the column list below
    df_rule_hits = pd.DataFrame(rule_hits_data, columns=[
        "order_id", "rule_id", "rule_name", "rule_description", "created_at"
    ])
    
    # 8. Output to new CSVs
    df.to_csv(output_orders_path, index=False)
    df_rule_hits.to_csv(output_rule_hits_path, index=False)
    
    print(f"Successfully processed {len(df)} orders.")
    print(f"Saved main results to: {output_orders_path}")
    print(f"Saved {len(df_rule_hits)} rule hits to: {output_rule_hits_path}")
    
    return df, df_rule_hits

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    DB_PARAMS = {
        "dbname": "ecommerce_fraud",
        "user": "postgres",
        "password": "Master#123",
        "host": "localhost",
        "port": 5434
    }
    
    input_file = r"data_csv\orders 1.csv"
    output_orders = r"data_csv\orders_output_1.csv"
    output_rule_hits = r"data_csv\order_rule_hit_1.csv"
    
    result_df, rule_hits_df = process_orders_csv(input_file, output_orders, output_rule_hits, DB_PARAMS)