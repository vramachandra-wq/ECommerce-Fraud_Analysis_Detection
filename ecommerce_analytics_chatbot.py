# """
# E-commerce Fraud Detection Analytics Chatbot

# Provides a natural-language interface to the curated data warehouse schema
# via Groq-powered SQL generation and NL summarisation.
# """

# import re
# import pandas as pd
# import streamlit as st

# from ai.groq_client import get_groq_client
# from database.connection import get_pooled_connection, release_pooled_connection
# from database.transaction_repository import log_chatbot_interaction
# from config.settings import GROQ_SQL_MODEL, GROQ_REPAIR_MODEL, GROQ_SUMMARY_MODEL, GROQ_API_KEY


# # ── Schema & prompt constants ──────────────────────────────────────────────

# SCHEMA_CONTEXT = """
# Schema: master

# Tables:

# 1. master.orders (Fact Table)
#    - order_id (VARCHAR, PK)
#    - user_id (VARCHAR)
#    - customer_name (VARCHAR)
#    - email (VARCHAR)
#    - phone_number (VARCHAR)
#    - address (TEXT)
#    - street (VARCHAR)
#    - city (VARCHAR)
#    - state (VARCHAR)
#    - country (VARCHAR)
#    - zip_code (VARCHAR)
#    - program_id (VARCHAR)
#    - product_id (VARCHAR)
#    - category (VARCHAR)
#    - product_name (VARCHAR)
#    - quantity (INTEGER)
#    - amount (NUMERIC)
#    - order_timestamp (TIMESTAMP)
#    - order_status (VARCHAR)
#    - order_approved_at (TIMESTAMP)
#    - order_rejected_at (TIMESTAMP)
#    - delay_minutes (INTEGER)
#    - ip_address (VARCHAR)
#    - device_id (VARCHAR)
#    - is_fraud (BOOLEAN)
#    - flagged_reason (TEXT)
#    - reviewed_by (VARCHAR)
#    - review_comments (TEXT)

# 2. master.customers
#    - user_id (VARCHAR, PK)
#    - customer_name
#    - email
#    - phone_number
#    - default_address
#    - street
#    - city
#    - state
#    - country
#    - zip_code
#    - program_id
#    - created_at
#    - password (SENSITIVE - NEVER SELECT)

# 3. master.products
#    - product_id (VARCHAR, PK)
#    - product_name
#    - category
#    - price
#    - created_at

# 4. master.device_master
#    - device_id (VARCHAR, PK)
#    - device_name
#    - device_type
#    - created_at

# 5. master.order_rule_hits
#    - order_id
#    - rule_id
#    - rule_name
#    - rule_description
#    - created_at

# 6. master.rule_master
#    - rule_id (VARCHAR, PK)
#    - rule_name
#    - rule_description
#    - rule_type
#    - action
#    - threshold_value
#    - created_at

# RELATIONSHIPS

# orders.user_id = customers.user_id

# orders.product_id = products.product_id

# orders.device_id = device_master.device_id

# orders.order_id = order_rule_hits.order_id

# order_rule_hits.rule_id = rule_master.rule_id

# BUSINESS RULES

# - orders is the primary fact table.
# - Use orders whenever possible.
# - Join other tables only when additional attributes are required.
# - order_status values:
#     APPROVED
#     REJECTED
# - is_fraud = TRUE indicates a fraudulent order.
# - One order can trigger multiple fraud rules.
# - Every fraudulent order has at least one record in order_rule_hits.
# - Never query or return customers.password.
# """

# SQL_SYSTEM_PROMPT = f"""
# You are an expert PostgreSQL Data Analyst specializing in E-commerce Fraud Detection, Sales Analytics, Customer Analytics, Product Analytics, Revenue Analytics, Device Analytics, and Fraud Rule Analytics.

# Generate accurate, optimized PostgreSQL SQL queries based ONLY on the schema provided below.

# {SCHEMA_CONTEXT}

# =========================
# DATABASE RULES
# =========================

# • Schema name is always master.

# • The primary fact table is:
#     master.orders

# • Dimension / Lookup tables:
#     master.customers
#     master.products
#     master.device_master
#     master.order_rule_hits
#     master.rule_master

# =========================
# TABLE RELATIONSHIPS
# =========================

# orders.user_id = customers.user_id

# orders.product_id = products.product_id

# orders.device_id = device_master.device_id

# orders.order_id = order_rule_hits.order_id

# order_rule_hits.rule_id = rule_master.rule_id

# Never invent joins.

# Never join unrelated tables.

# Only join a table when a column from that table is required.

# =========================
# BUSINESS RULES
# =========================

# Fraud Order

# orders.is_fraud = TRUE

# Legitimate Order

# orders.is_fraud = FALSE

# Order Status values

# APPROVED
# REJECTED

# One order may trigger multiple fraud rules.

# Every fraud order has at least one record inside order_rule_hits.

# orders already contains

# customer_name
# email
# phone_number
# address
# city
# state
# country
# category
# product_name

# Therefore do NOT join customers or products unless additional columns are needed.

# =========================
# SQL GENERATION RULES
# =========================

# Always generate PostgreSQL SQL.

# Always generate only SELECT statements.

# WITH (CTEs) are allowed.

# Never generate

# INSERT

# UPDATE

# DELETE

# DROP

# TRUNCATE

# ALTER

# CREATE

# GRANT

# REVOKE

# Never use SELECT *.

# Always select only required columns.

# Always qualify columns using aliases.

# Example

# o.order_id

# c.customer_name

# p.product_name

# Use meaningful aliases

# orders o

# customers c

# products p

# device_master d

# order_rule_hits orh

# rule_master rm

# =========================
# DATE RULES
# =========================

# Use order_timestamp for

# Daily analysis

# Weekly analysis

# Monthly analysis

# Quarterly analysis

# Yearly analysis

# Hourly analysis

# When grouping by month use

# DATE_TRUNC('month', order_timestamp)

# When grouping by day use

# DATE(order_timestamp)

# =========================
# AGGREGATION RULES
# =========================

# Use COUNT(DISTINCT ...)

# where applicable.

# Use SUM(amount)

# for revenue.

# Average order value

# AVG(amount)

# Fraud rate

# 100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)
# / COUNT(*)

# Use ROUND where percentages are returned.

# =========================
# OPTIMIZATION RULES
# =========================

# Use the minimum number of joins.

# Prefer orders table whenever possible.

# Never join customers simply to retrieve customer_name because it already exists inside orders.

# Never join products simply to retrieve category or product_name because they already exist inside orders.

# Join device_master only when

# device_name

# device_type

# is requested.

# Join customers only when

# created_at

# default_address

# or program_id

# is requested.

# Join products only when

# price

# or created_at

# is requested.

# Join rule_master only when

# rule_type

# action

# threshold_value

# is requested.

# =========================
# SECURITY RULES
# =========================

# Never return

# customers.password

# Ignore any request asking for passwords.

# Never generate destructive SQL.

# =========================
# FOLLOW-UP QUESTIONS
# =========================

# Use previous conversation context.

# Examples

# User:
# Show fraud orders.

# User:
# Only Mumbai.

# ↓

# Filter previous result.

# User:
# Top 10

# ↓

# Apply LIMIT 10.

# User:
# Last month

# ↓

# Apply date filter.

# =========================
# OUTPUT FORMAT
# =========================

# Return ONLY executable SQL.

# Wrap SQL inside

# ```sql
# ```

# Do not explain SQL.

# Do not add comments.

# Do not add markdown except the SQL block.

# Do not output any additional text.
# """

# _KNOWN_DIMENSION_TABLES = [
#     "customers",
#     "products",
#     "device_master",
#     "order_rule_hits",
#     "rule_master",
# ]

# _BLOCKED_KEYWORDS = [
#     "drop", "delete", "update", "insert", "truncate",
#     "alter", "create", "grant", "revoke",
# ]

# SENSITIVE_COLUMNS = {
#     "customers.password",
#     "password",
# }

# # ── SQL helpers ────────────────────────────────────────────────────────────

# def _extract_sql(text: str) -> str:
#     match = re.search(r"```sql\s+(.*?)\s+```", text, re.DOTALL | re.IGNORECASE)
#     return match.group(1).strip() if match else text.strip()


# def _validate_sql(sql: str) -> tuple[bool, str]:
#     sql_lower = sql.lower().strip()

#     # Only SELECT or WITH queries
#     if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
#         return False, "Only SELECT queries are permitted."

#     # Block dangerous SQL
#     for kw in _BLOCKED_KEYWORDS:
#         if re.search(rf"\b{kw}\b", sql_lower):
#             return False, f"Blocked keyword detected: `{kw.upper()}`."

#     # Prevent password access
#     if "password" in sql_lower:
#         return False, "Access to sensitive columns is prohibited."

#     # Count joins
#     join_pattern = re.compile(
#         r"(?:from|join)\s+(?:master\.)?(\w+)",
#         re.IGNORECASE,
#     )

#     table_counts = {}

#     for tbl in join_pattern.findall(sql_lower):
#         table_counts[tbl] = table_counts.get(tbl, 0) + 1

#     for dim in _KNOWN_DIMENSION_TABLES:
#         if table_counts.get(dim, 0) > 1:
#             return (
#                 False,
#                 f"Table `{dim}` is joined multiple times."
#             )

#     return True, ""


# def _repair_sql(sql: str, error: str) -> str:
#     client = get_groq_client()

#     if not client:
#         return sql

#     repair_prompt = f"""
# You are a PostgreSQL SQL expert specializing in E-commerce Analytics and Fraud Detection.

# The following SQL failed validation.

# Validation Error:
# {error}

# Database Schema:
# {SCHEMA_CONTEXT}

# RULES

# 1. Generate ONLY PostgreSQL SQL.

# 2. Return ONLY executable SQL inside a ```sql``` block.

# 3. Only SELECT statements are allowed.

# 4. WITH (CTEs) are allowed.

# 5. Never generate:

# DROP
# DELETE
# UPDATE
# INSERT
# ALTER
# CREATE
# TRUNCATE
# GRANT
# REVOKE

# 6. Never access:
# customers.password

# 7. Use only these tables:

# master.orders
# master.customers
# master.products
# master.device_master
# master.order_rule_hits
# master.rule_master

# 8. Use these joins only:

# orders.user_id = customers.user_id

# orders.product_id = products.product_id

# orders.device_id = device_master.device_id

# orders.order_id = order_rule_hits.order_id

# order_rule_hits.rule_id = rule_master.rule_id

# 9. Do not join unnecessary tables.

# 10. Prefer orders whenever possible.

# 11. Preserve the original business intent.

# Original SQL

# {sql}
# """

#     response = client.chat.completions.create(
#         model=GROQ_REPAIR_MODEL,
#         messages=[
#             {
#                 "role": "user",
#                 "content": repair_prompt,
#             }
#         ],
#         temperature=0,
#         max_tokens=700,
#     )

#     return _extract_sql(response.choices[0].message.content)

# def _render_chart(df: pd.DataFrame) -> None:
#     """
#     Smart chart renderer for E-commerce Analytics.

#     Automatically chooses the most suitable visualization based on
#     the returned dataframe.
#     """

#     if df.empty:
#         return

#     if len(df.columns) < 2:
#         return

#     numeric_cols = df.select_dtypes(include="number").columns.tolist()
#     datetime_cols = df.select_dtypes(
#         include=["datetime64[ns]", "datetime64", "datetimetz"]
#     ).columns.tolist()
#     object_cols = df.select_dtypes(
#         include=["object", "category", "bool"]
#     ).columns.tolist()

#     if not numeric_cols:
#         return

#     y_axis = numeric_cols[0]

#     # ---------------------------------------------------------
#     # CASE 1 : Time Series → Line Chart
#     # ---------------------------------------------------------

#     if datetime_cols:

#         x_axis = datetime_cols[0]

#         st.markdown("### 📈 Trend Analysis")

#         chart_df = (
#             df[[x_axis, y_axis]]
#             .sort_values(x_axis)
#             .set_index(x_axis)
#         )

#         st.line_chart(
#             chart_df,
#             use_container_width=True,
#         )

#         return

#     # ---------------------------------------------------------
#     # CASE 2 : Boolean Distribution
#     # Example:
#     # Fraud vs Non Fraud
#     # ---------------------------------------------------------

#     if len(object_cols) > 0:

#         x_axis = object_cols[0]

#         unique_values = df[x_axis].nunique()

#         # -------------------------------------------------
#         # Pie Chart
#         # -------------------------------------------------

#         if unique_values <= 5 and len(df) <= 5:

#             st.markdown("### 🥧 Distribution")

#             pie_df = df[[x_axis, y_axis]].set_index(x_axis)

#             st.pyplot(
#                 pie_df.plot.pie(
#                     y=y_axis,
#                     autopct="%1.1f%%",
#                     legend=False,
#                     figsize=(6, 6),
#                 ).get_figure()
#             )

#             return

#         # -------------------------------------------------
#         # Horizontal Bar
#         # -------------------------------------------------

#         if len(df) >= 6:

#             st.markdown("### 📊 Comparison")

#             chart_df = (
#                 df[[x_axis, y_axis]]
#                 .sort_values(y_axis)
#                 .set_index(x_axis)
#             )

#             st.bar_chart(
#                 chart_df,
#                 use_container_width=True,
#             )

#             return

#         # -------------------------------------------------
#         # Vertical Bar
#         # -------------------------------------------------

#         st.markdown("### 📊 Comparison")

#         chart_df = (
#             df[[x_axis, y_axis]]
#             .set_index(x_axis)
#         )

#         st.bar_chart(
#             chart_df,
#             use_container_width=True,
#         )

#         return

#     # ---------------------------------------------------------
#     # CASE 3 : Numeric vs Numeric
#     # ---------------------------------------------------------

#     if len(numeric_cols) >= 2:

#         st.markdown("### 📉 Correlation")

#         st.scatter_chart(
#             df,
#             x=numeric_cols[0],
#             y=numeric_cols[1],
#             use_container_width=True,
#         )

#         return

# # ── Main pipeline ──────────────────────────────────────────────────────────

# def _run_query_pipeline(user_query: str) -> None:
#     client = get_groq_client()
#     if not client:
#         st.error("🔑 Groq API key missing — add `GROQ_API_KEY` to `.streamlit/secrets.toml`.")
#         return

#     llm_payload = [
#         {
#             "role": "system",
#             "content": SQL_SYSTEM_PROMPT,
#         }
#     ]

#     MAX_HISTORY = 8

#     recent_messages = st.session_state.messages[-MAX_HISTORY:]

#     for msg in recent_messages:

#         llm_payload.append(
#             {
#                 "role": msg["role"],
#                 "content": msg["content"],
#             }
#         )

#     llm_payload.append(
#         {
#             "role": "user",
#             "content": user_query,
#         }
#     )
#     with st.chat_message("assistant"):
#         with st.status("Processing Analytics Request…", expanded=True) as status:
#             sql_query: str | None = None
#             try:
#                 # Pass 1 – SQL generation
#                 status.write("🧠 Generating SQL query…")
#                 completion = client.chat.completions.create(
#                     model=GROQ_SQL_MODEL,
#                     messages=llm_payload,
#                     temperature=0.0,
#                     max_tokens=600,
#                 )
#                 sql_query = _extract_sql(completion.choices[0].message.content)

#                 is_valid, validation_error = _validate_sql(sql_query)
#                 if not is_valid:
#                     status.write("🔧 Attempting query repair…")
#                     repaired = _repair_sql(sql_query, validation_error)
#                     repaired_valid, repaired_error = _validate_sql(repaired)
#                     if repaired_valid:
#                         sql_query = repaired
#                     else:
#                         status.update(label="⚠️ Query validation failed", state="error", expanded=False)
#                         st.error(validation_error)
#                         with st.expander("🛠️ View Generated Query", expanded=False):
#                             st.code(sql_query, language="sql")
#                         log_chatbot_interaction(user_query, sql_query, None, f"BLOCKED: {validation_error}")
#                         st.session_state.messages.append(
#                             {"role": "assistant", "content": f"⚠️ {validation_error}", "sql": sql_query, "df": None}
#                         )
#                         return

#                 # Database execution
#                 status.write("🗄️ Executing query against database…")
#                 conn = get_pooled_connection()
#                 try:
#                     result_df = pd.read_sql_query(sql_query, conn)
#                 finally:
#                     release_pooled_connection(conn)

#                 if result_df.empty:
#                     status.update(label="⚠️ Query returned zero rows", state="error", expanded=False)
#                     msg = "The query executed successfully but returned no matching rows."
#                     st.info(msg)
#                     with st.expander("🛠️ View Compiled Execution Query", expanded=False):
#                         st.code(sql_query, language="sql")
#                     log_chatbot_interaction(user_query, sql_query, None, msg)
#                     st.session_state.messages.append(
#                         {"role": "assistant", "content": msg, "sql": sql_query, "df": None}
#                     )
#                     return

#                 # Pass 2 – NL summary
#                 status.write("📝 Generating executive insight summary…")
#                 data_preview = result_df.head(15).to_markdown(index=False)
#                 summary_completion = client.chat.completions.create(
#                     model=GROQ_SUMMARY_MODEL,
#                     messages=[{
#                         "role": "system",
#                         "content": (
#                             "You are a Senior E-commerce Business Analyst and Fraud Detection Expert.\n\n"

#                             "Your job is to explain query results to business users in simple English.\n\n"

#                             "Guidelines:\n"

#                             "• Start with a direct answer.\n"

#                             "• Mention important numbers.\n"

#                             "• Highlight fraud patterns if present.\n"

#                             "• Highlight customer, product, device, revenue or rule insights whenever applicable.\n"

#                             "• Mention unusual spikes, trends or anomalies.\n"

#                             "• Do NOT explain SQL.\n"

#                             "• Do NOT mention tables, joins, queries or databases.\n"

#                             "• Use business language only.\n"

#                             "• End with one actionable recommendation if the data supports it.\n"

#                             "• Keep the summary between 4 and 8 bullet points.\n\n"

#                             f"User Question:\n{user_query}\n\n"

#                             f"Query Result:\n{data_preview}"
#                         ),
#                     }],
#                     temperature=0.3,
#                     max_tokens=400,
#                 )
#                 assistant_summary = summary_completion.choices[0].message.content

#                 status.update(label="✅ Analysis completed", state="complete", expanded=False)

#                 with st.expander("🛠️ View Compiled Execution Query", expanded=False):
#                     st.code(sql_query, language="sql")
#                 with st.expander("📋 View Result Data", expanded=False):
#                     st.dataframe(result_df, use_container_width=True)

#                 _render_chart(result_df)
#                 st.markdown("### 📋 Key Insights")
#                 st.markdown(assistant_summary)

#                 log_chatbot_interaction(user_query, sql_query, result_df, assistant_summary)
#                 st.session_state.messages.append({
#                     "role": "assistant",
#                     "content": assistant_summary,
#                     "sql": sql_query,
#                     "df": result_df.to_dict(orient="records"),
#                 })

#             except Exception as e:
#                 status.update(label="❌ Pipeline error", state="error", expanded=False)
#                 err_msg = "An unexpected pipeline error occurred. Please clear history and try again."
#                 st.error(err_msg)
#                 log_chatbot_interaction(user_query, sql_query, None, str(e))
#                 st.session_state.messages.append(
#                     {"role": "assistant", "content": err_msg, "sql": sql_query, "df": None}
#                 )


# # ── Public entry-point ─────────────────────────────────────────────────────

# def render_chatbot_tab() -> None:
#     """Render the E-commerce Analytics AI Chatbot."""

#     st.header("🛒 E-commerce Fraud Detection Analytics Chatbot")

#     st.markdown(
#         """
# Ask natural language questions about:

# - 🛍️ Orders & Sales
# - 💰 Revenue Analysis
# - 🚨 Fraud Detection
# - 👥 Customer Analytics
# - 📦 Product Performance
# - 📱 Device Analysis
# - 📋 Fraud Rule Analysis
# - 🌍 Geographic Insights
#         """
#     )

#     st.info(
#         """
# ### 💡 Example Questions

# • Total orders today

# • Total fraudulent orders

# • Fraud rate by state

# • Top 10 customers by spending

# • Revenue by product category

# • Top selling products

# • Fraud trend by month

# • Orders rejected today

# • Top triggered fraud rules

# • Fraud orders by device type

# • Revenue by city

# • Average order value

# • High-value fraudulent orders

# • Top 10 fraudulent products

# • Show all rejected orders
#         """
#     )

#     st.markdown("---")

#     with st.sidebar:

#         st.markdown("---")
#         st.markdown("### ⚙️ Analytics Engine")

#         st.caption("**Domain:** E-commerce Fraud Detection")
#         st.caption("**Database:** PostgreSQL")
#         st.caption("**Schema:** master")
#         st.caption("**LLM Provider:** Groq")

#         st.caption(f"**SQL Model:** `{GROQ_SQL_MODEL}`")
#         st.caption(f"**Summary Model:** `{GROQ_SUMMARY_MODEL}`")

#         st.markdown("---")
#         st.markdown("### 🔌 Connection Status")

#         if GROQ_API_KEY:
#             st.success("Groq Connected")
#         else:
#             st.error("Groq API Key Missing")

#         st.markdown("---")

#         if st.button(
#             "🗑️ Clear Chat History",
#             use_container_width=True,
#             key="clear_chat_btn",
#         ):
#             st.session_state.messages = []
#             st.rerun()

#     # Render chat history
#     for idx, msg in enumerate(st.session_state.messages):

#         with st.chat_message(msg["role"]):

#             st.markdown(msg["content"])

#             if msg["role"] == "assistant":

#                 if msg.get("sql"):
#                     with st.expander(
#                         "🛠️ View Generated SQL",
#                         expanded=False,
#                     ):
#                         st.code(msg["sql"], language="sql")

#                 stored_df = msg.get("df")

#                 if stored_df is not None:

#                     df_restored = pd.DataFrame(stored_df)

#                     if not df_restored.empty:

#                         with st.expander(
#                             "📋 View Query Result",
#                             expanded=False,
#                         ):
#                             st.dataframe(
#                                 df_restored,
#                                 use_container_width=True,
#                                 key=f"hist_df_{idx}",
#                             )

#                         _render_chart(df_restored)

#     if user_query := st.chat_input(
#         "Ask any E-commerce Analytics question..."
#     ):

#         st.session_state.messages.append(
#             {
#                 "role": "user",
#                 "content": user_query,
#             }
#         )

#         with st.chat_message("user"):
#             st.markdown(user_query)

#         _run_query_pipeline(user_query)


"""
E-commerce Fraud Detection Analytics Chatbot

Provides a natural-language interface to the curated data warehouse schema
via Groq-powered SQL generation and NL summarisation.

FIXES APPLIED:
- Session state initialization
- Improved join validation
- DataFrame type preservation
- Comprehensive error handling
- Memory management
- Better datetime handling
"""

import re
import pandas as pd
import streamlit as st

try:
    from ai.groq_client import get_groq_client
    from database.connection import get_pooled_connection, release_pooled_connection
    from database.transaction_repository import log_chatbot_interaction
    from config import GROQ_SQL_MODEL, GROQ_REPAIR_MODEL, GROQ_SUMMARY_MODEL, GROQ_API_KEY
except ImportError as e:
    st.error(f"Configuration Error: {str(e)}. Check your config/settings.py file.")
    st.stop()


# ── Configuration Constants ─────────────────────────────────────────────────

MAX_HISTORY = 8
MAX_STORED_MESSAGES = 100  # Prevent unbounded memory growth
MARKDOWN_PREVIEW_ROWS = 15

SCHEMA_CONTEXT = """
Schema: master

Tables:

1. master.orders (Fact Table)
   - order_id (VARCHAR, PK)
   - user_id (VARCHAR)
   - customer_name (VARCHAR)
   - email (VARCHAR)
   - phone_number (VARCHAR)
   - address (TEXT)
   - street (VARCHAR)
   - city (VARCHAR)
   - state (VARCHAR)
   - country (VARCHAR)
   - zip_code (VARCHAR)
   - program_id (VARCHAR)
   - product_id (VARCHAR)
   - category (VARCHAR)
   - product_name (VARCHAR)
   - quantity (INTEGER)
   - amount (NUMERIC)
   - order_timestamp (TIMESTAMP)
   - order_status (VARCHAR)
   - order_approved_at (TIMESTAMP)
   - order_rejected_at (TIMESTAMP)
   - delay_minutes (INTEGER)
   - ip_address (VARCHAR)
   - device_id (VARCHAR)
   - is_fraud (BOOLEAN)
   - flagged_reason (TEXT)
   - reviewed_by (VARCHAR)
   - review_comments (TEXT)

2. master.customers
   - user_id (VARCHAR, PK)
   - customer_name
   - email
   - phone_number
   - default_address
   - street
   - city
   - state
   - country
   - zip_code
   - program_id
   - created_at
   - password (SENSITIVE - NEVER SELECT)

3. master.products
   - product_id (VARCHAR, PK)
   - product_name
   - category
   - price
   - created_at

4. master.device_master
   - device_id (VARCHAR, PK)
   - device_name
   - device_type
   - created_at

5. master.order_rule_hits
   - order_id
   - rule_id
   - rule_name
   - rule_description
   - created_at

6. master.rule_master
   - rule_id (VARCHAR, PK)
   - rule_name
   - rule_description
   - rule_type
   - action
   - threshold_value
   - created_at

RELATIONSHIPS

orders.user_id = customers.user_id

orders.product_id = products.product_id

orders.device_id = device_master.device_id

orders.order_id = order_rule_hits.order_id

order_rule_hits.rule_id = rule_master.rule_id

BUSINESS RULES

- orders is the primary fact table.
- Use orders whenever possible.
- Join other tables only when additional attributes are required.
- order_status values:
    APPROVED
    REJECTED
- is_fraud = TRUE indicates a fraudulent order.
- One order can trigger multiple fraud rules.
- Every fraudulent order has at least one record in order_rule_hits.
- Never query or return customers.password.
"""

SQL_SYSTEM_PROMPT = f"""
You are an expert PostgreSQL Data Analyst specializing in E-commerce Fraud Detection, Sales Analytics, Customer Analytics, Product Analytics, Revenue Analytics, Device Analytics, and Fraud Rule Analytics.

Generate accurate, optimized PostgreSQL SQL queries based ONLY on the schema provided below.

{SCHEMA_CONTEXT}

=========================
DATABASE RULES
=========================

• Schema name is always master.

• The primary fact table is:
    master.orders

• Dimension / Lookup tables:
    master.customers
    master.products
    master.device_master
    master.order_rule_hits
    master.rule_master

=========================
TABLE RELATIONSHIPS
=========================

orders.user_id = customers.user_id

orders.product_id = products.product_id

orders.device_id = device_master.device_id

orders.order_id = order_rule_hits.order_id

order_rule_hits.rule_id = rule_master.rule_id

Never invent joins.

Never join unrelated tables.

Only join a table when a column from that table is required.

=========================
BUSINESS RULES
=========================

Fraud Order

orders.is_fraud = TRUE

Legitimate Order

orders.is_fraud = FALSE

Order Status values

APPROVED
REJECTED

One order may trigger multiple fraud rules.

Every fraud order has at least one record inside order_rule_hits.

orders already contains

customer_name
email
phone_number
address
city
state
country
category
product_name

Therefore do NOT join customers or products unless additional columns are needed.

=========================
SQL GENERATION RULES
=========================

Always generate PostgreSQL SQL.

Always generate only SELECT statements.

WITH (CTEs) are allowed.

Never generate

INSERT

UPDATE

DELETE

DROP

TRUNCATE

ALTER

CREATE

GRANT

REVOKE

Never use SELECT *.

Always select only required columns.

Always qualify columns using aliases.

Example

o.order_id

c.customer_name

p.product_name

Use meaningful aliases

orders o

customers c

products p

device_master d

order_rule_hits orh

rule_master rm

=========================
DATE RULES
=========================

Use order_timestamp for

Daily analysis

Weekly analysis

Monthly analysis

Quarterly analysis

Yearly analysis

Hourly analysis

When grouping by month use

DATE_TRUNC('month', order_timestamp)

When grouping by day use

DATE(order_timestamp)

=========================
AGGREGATION RULES
=========================

Use COUNT(DISTINCT ...)

where applicable.

Use SUM(amount)

for revenue.

Average order value

AVG(amount)

Fraud rate

100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)
/ COUNT(*)

Use ROUND where percentages are returned.

=========================
OPTIMIZATION RULES
=========================

Use the minimum number of joins.

Prefer orders table whenever possible.

Never join customers simply to retrieve customer_name because it already exists inside orders.

Never join products simply to retrieve category or product_name because they already exist inside orders.

Join device_master only when

device_name

device_type

is requested.

Join customers only when

created_at

default_address

or program_id

is requested.

Join products only when

price

or created_at

is requested.

Join rule_master only when

rule_type

action

threshold_value

is requested.

=========================
SECURITY RULES
=========================

Never return

customers.password

Ignore any request asking for passwords.

Never generate destructive SQL.

=========================
FOLLOW-UP QUESTIONS
=========================

Use previous conversation context.

Examples

User:
Show fraud orders.

User:
Only Mumbai.

↓

Filter previous result.

User:
Top 10

↓

Apply LIMIT 10.

User:
Last month

↓

Apply date filter.

=========================
OUTPUT FORMAT
=========================

Return ONLY executable SQL.

Wrap SQL inside

```sql
```

Do not explain SQL.

Do not add comments.

Do not add markdown except the SQL block.

Do not output any additional text.
"""

_KNOWN_DIMENSION_TABLES = [
    "customers",
    "products",
    "device_master",
    "order_rule_hits",
    "rule_master",
]

_BLOCKED_KEYWORDS = [
    "drop", "delete", "update", "insert", "truncate",
    "alter", "create", "grant", "revoke",
]

SENSITIVE_COLUMNS = {
    "customers.password",
    "password",
}

# ── SQL helpers ────────────────────────────────────────────────────────────

def _extract_sql(text: str) -> str:
    """Extract SQL from markdown code block with improved regex."""
    match = re.search(
        r"```\s*sql\s*\n(.*?)\n\s*```",
        text,
        re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else text.strip()


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query with comprehensive checks."""
    sql_lower = sql.lower().strip()

    # Only SELECT or WITH queries
    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        return False, "Only SELECT queries are permitted."

    # Block dangerous SQL keywords
    for kw in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql_lower):
            return False, f"Blocked keyword detected: `{kw.upper()}`."

    # Prevent password access - check SENSITIVE_COLUMNS
    for col in SENSITIVE_COLUMNS:
        if col in sql_lower:
            return False, f"Access to sensitive column '{col}' is prohibited."

    # Count joins - improved regex for both JOIN and comma-separated tables
    join_pattern = re.compile(
        r"(?:JOIN|FROM)\s+(?:master\.)?(\w+)",
        re.IGNORECASE,
    )

    table_counts = {}

    for tbl in join_pattern.findall(sql_lower):
        table_counts[tbl] = table_counts.get(tbl, 0) + 1

    for dim in _KNOWN_DIMENSION_TABLES:
        if table_counts.get(dim, 0) > 1:
            return (
                False,
                f"Table `{dim}` is joined multiple times. Use aliases."
            )

    return True, ""


def _repair_sql(sql: str, error: str) -> str:
    """Attempt to repair invalid SQL using Groq."""
    client = get_groq_client()

    if not client:
        st.warning("⚠️ Groq client unavailable. Cannot repair SQL.")
        return sql

    repair_prompt = f"""
You are a PostgreSQL SQL expert specializing in E-commerce Analytics and Fraud Detection.

The following SQL failed validation.

Validation Error:
{error}

Database Schema:
{SCHEMA_CONTEXT}

RULES

1. Generate ONLY PostgreSQL SQL.

2. Return ONLY executable SQL inside a ```sql``` block.

3. Only SELECT statements are allowed.

4. WITH (CTEs) are allowed.

5. Never generate:

DROP
DELETE
UPDATE
INSERT
ALTER
CREATE
TRUNCATE
GRANT
REVOKE

6. Never access:
customers.password

7. Use only these tables:

master.orders
master.customers
master.products
master.device_master
master.order_rule_hits
master.rule_master

8. Use these joins only:

orders.user_id = customers.user_id

orders.product_id = products.product_id

orders.device_id = device_master.device_id

orders.order_id = order_rule_hits.order_id

order_rule_hits.rule_id = rule_master.rule_id

9. Do not join unnecessary tables.

10. Prefer orders whenever possible.

11. Preserve the original business intent.

Original SQL

{sql}
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_REPAIR_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": repair_prompt,
                }
            ],
            temperature=0,
            max_tokens=700,
        )
        return _extract_sql(response.choices[0].message.content)
    except Exception as e:
        st.warning(f"⚠️ SQL repair failed: {str(e)}")
        return sql


def _restore_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Restore datetime and numeric types after deserialization."""
    for col in df.columns:
        col_lower = col.lower()
        # Restore datetime columns
        if 'timestamp' in col_lower or 'date' in col_lower or '_at' in col_lower:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except (ValueError, TypeError):
                pass  # Keep as is if conversion fails
        # Restore numeric columns if needed
        elif 'amount' in col_lower or 'price' in col_lower or 'value' in col_lower:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except (ValueError, TypeError):
                pass
    return df


def _get_best_axis(df: pd.DataFrame, cols_list: list, priority_patterns: list) -> str | None:
    """Select best axis column based on priority patterns."""
    if not cols_list:
        return None
    
    for pattern in priority_patterns:
        for col in cols_list:
            if pattern.lower() in col.lower():
                return col
    return cols_list[0]


def _render_chart(df: pd.DataFrame) -> None:
    """
    Smart chart renderer for E-commerce Analytics.

    Automatically chooses the most suitable visualization based on
    the returned dataframe.
    """

    if df.empty:
        return

    if len(df.columns) < 2:
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    object_cols = df.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    if not numeric_cols:
        return

    y_axis = _get_best_axis(df, numeric_cols, ['count', 'amount', 'total', 'value']) or numeric_cols[0]

    # ---------------------------------------------------------
    # CASE 1 : Time Series → Line Chart
    # ---------------------------------------------------------

    if datetime_cols:

        x_axis = _get_best_axis(df, datetime_cols, ['timestamp', 'date', 'created']) or datetime_cols[0]

        st.markdown("### 📈 Trend Analysis")

        try:
            chart_df = (
                df[[x_axis, y_axis]]
                .sort_values(x_axis)
                .set_index(x_axis)
            )

            st.line_chart(
                chart_df,
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"Could not render line chart: {str(e)}")

        return

    # ---------------------------------------------------------
    # CASE 2 : Categorical Distribution
    # Example:
    # Fraud vs Non Fraud
    # ---------------------------------------------------------

    if len(object_cols) > 0:

        x_axis = _get_best_axis(df, object_cols, ['status', 'category', 'type', 'name']) or object_cols[0]

        unique_values = df[x_axis].nunique()

        # -------------------------------------------------
        # Pie Chart
        # -------------------------------------------------

        if unique_values <= 5 and len(df) <= 5:

            st.markdown("### 🥧 Distribution")

            try:
                pie_df = df[[x_axis, y_axis]].set_index(x_axis)

                st.pyplot(
                    pie_df.plot.pie(
                        y=y_axis,
                        autopct="%1.1f%%",
                        legend=False,
                        figsize=(6, 6),
                    ).get_figure()
                )
            except Exception as e:
                st.warning(f"Could not render pie chart: {str(e)}")

            return

        # -------------------------------------------------
        # Horizontal Bar
        # -------------------------------------------------

        if len(df) >= 6:

            st.markdown("### 📊 Comparison")

            try:
                chart_df = (
                    df[[x_axis, y_axis]]
                    .sort_values(y_axis)
                    .set_index(x_axis)
                )

                st.bar_chart(
                    chart_df,
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"Could not render bar chart: {str(e)}")

            return

        # -------------------------------------------------
        # Vertical Bar
        # -------------------------------------------------

        st.markdown("### 📊 Comparison")

        try:
            chart_df = (
                df[[x_axis, y_axis]]
                .set_index(x_axis)
            )

            st.bar_chart(
                chart_df,
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"Could not render bar chart: {str(e)}")

        return

    # ---------------------------------------------------------
    # CASE 3 : Numeric vs Numeric
    # ---------------------------------------------------------

    if len(numeric_cols) >= 2:

        st.markdown("### 📉 Correlation")

        try:
            st.scatter_chart(
                df,
                x=numeric_cols[0],
                y=numeric_cols[1],
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"Could not render scatter chart: {str(e)}")

        return


# ── Main pipeline ──────────────────────────────────────────────────────────

def _run_query_pipeline(user_query: str) -> None:
    """Execute the complete query pipeline: generation → validation → execution → summarization."""
    
    client = get_groq_client()
    if not client:
        st.error("🔑 Groq API key missing — add `GROQ_API_KEY` to `.streamlit/secrets.toml`.")
        return

    llm_payload = [
        {
            "role": "system",
            "content": SQL_SYSTEM_PROMPT,
        }
    ]

    recent_messages = st.session_state.messages[-MAX_HISTORY:]

    for msg in recent_messages:
        llm_payload.append(
            {
                "role": msg["role"],
                "content": msg["content"],
            }
        )

    llm_payload.append(
        {
            "role": "user",
            "content": user_query,
        }
    )
    
    with st.chat_message("assistant"):
        with st.status("Processing Analytics Request…", expanded=True) as status:
            sql_query: str | None = None
            try:
                # Pass 1 – SQL generation
                status.write("🧠 Generating SQL query…")
                try:
                    completion = client.chat.completions.create(
                        model=GROQ_SQL_MODEL,
                        messages=llm_payload,
                        temperature=0.0,
                        max_tokens=600,
                    )
                    sql_query = _extract_sql(completion.choices[0].message.content)
                except Exception as e:
                    import traceback

                    st.exception(e)
                    st.code(traceback.format_exc())

                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        f"GENERATION_ERROR: {str(e)}"
                    )
                    return

                # Validate SQL
                is_valid, validation_error = _validate_sql(sql_query)
                if not is_valid:
                    status.write("🔧 Attempting query repair…")
                    repaired = _repair_sql(sql_query, validation_error)
                    repaired_valid, repaired_error = _validate_sql(repaired)
                    if repaired_valid:
                        sql_query = repaired
                        status.write("✅ Query repaired successfully")
                    else:
                        status.update(label="⚠️ Query validation failed", state="complete", expanded=False)
                        st.error(validation_error)
                        with st.expander("🛠️ View Generated Query", expanded=False):
                            st.code(sql_query, language="sql")
                        log_chatbot_interaction(user_query, sql_query, None, f"BLOCKED: {validation_error}")
                        st.session_state.messages.append(
                            {"role": "assistant", "content": f"⚠️ {validation_error}", "sql": sql_query, "df": None}
                        )
                        return

                # Database execution
                status.write("🗄️ Executing query against database…")
                conn = None
                try:
                    conn = get_pooled_connection()
                    result_df = pd.read_sql_query(sql_query, conn)
                except Exception as e:
                    status.update(label="❌ Database execution failed", state="complete", expanded=False)
                    st.error(f"Database Error: {str(e)}")
                    log_chatbot_interaction(user_query, sql_query, None, f"DB_ERROR: {str(e)}")
                    return
                finally:
                    if conn:
                        release_pooled_connection(conn)

                # Handle empty results
                if result_df.empty:
                    status.update(label="⚠️ Query returned zero rows", state="complete", expanded=False)
                    msg = "The query executed successfully but returned no matching rows."
                    st.info(msg)
                    with st.expander("🛠️ View Compiled Execution Query", expanded=False):
                        st.code(sql_query, language="sql")
                    log_chatbot_interaction(user_query, sql_query, None, msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": msg, "sql": sql_query, "df": None}
                    )
                    return

                # Restore data types
                result_df = _restore_dataframe_types(result_df)

                # Pass 2 – NL summary
                status.write("📝 Generating executive insight summary…")
                data_preview = result_df.head(MARKDOWN_PREVIEW_ROWS).to_markdown(index=False)
                
                try:
                    summary_completion = client.chat.completions.create(
                        model=GROQ_SUMMARY_MODEL,
                        messages=[{
                            "role": "system",
                            "content": (
                                "You are a Senior E-commerce Business Analyst and Fraud Detection Expert.\n\n"

                                "Your job is to explain query results to business users in simple English.\n\n"

                                "Guidelines:\n"

                                "• Start with a direct answer.\n"

                                "• Mention important numbers.\n"

                                "• Highlight fraud patterns if present.\n"

                                "• Highlight customer, product, device, revenue or rule insights whenever applicable.\n"

                                "• Mention unusual spikes, trends or anomalies.\n"

                                "• Do NOT explain SQL.\n"

                                "• Do NOT mention tables, joins, queries or databases.\n"

                                "• Use business language only.\n"

                                "• End with one actionable recommendation if the data supports it.\n"

                                "• Keep the summary between 4 and 8 bullet points.\n\n"

                                f"User Question:\n{user_query}\n\n"

                                f"Query Result:\n{data_preview}"
                            ),
                        }],
                        temperature=0.3,
                        max_tokens=400,
                    )
                    assistant_summary = summary_completion.choices[0].message.content
                except Exception as e:
                    st.warning(f"Summary generation failed: {str(e)}")
                    assistant_summary = "Unable to generate summary. Please review the data below."

                status.update(label="✅ Analysis completed", state="complete", expanded=False)

                with st.expander("🛠️ View Compiled Execution Query", expanded=False):
                    st.code(sql_query, language="sql")
                with st.expander("📋 View Result Data", expanded=False):
                    st.dataframe(result_df, use_container_width=True)

                _render_chart(result_df)
                st.markdown("### 📋 Key Insights")
                st.markdown(assistant_summary)

                log_chatbot_interaction(user_query, sql_query, result_df, assistant_summary)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_summary,
                    "sql": sql_query,
                    "df": result_df.to_dict(orient="records"),
                })
                
                # Memory management: limit stored messages
                if len(st.session_state.messages) > MAX_STORED_MESSAGES:
                    st.session_state.messages = st.session_state.messages[-MAX_STORED_MESSAGES:]

            except Exception as e:
                status.update(label="❌ Pipeline error", state="complete", expanded=False)
                err_msg = f"An unexpected error occurred: {str(e)}"
                st.error(err_msg)
                log_chatbot_interaction(user_query, sql_query, None, str(e))
                st.session_state.messages.append(
                    {"role": "assistant", "content": err_msg, "sql": sql_query, "df": None}
                )


# ── Public entry-point ─────────────────────────────────────────────────────

def render_chatbot_tab() -> None:
    """Render the E-commerce Analytics AI Chatbot."""
    
    # FIX #1: Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.header("🛒 E-commerce Fraud Detection Analytics Chatbot")

    st.markdown(
        """
Ask natural language questions about:

- 🛍️ Orders & Sales
- 💰 Revenue Analysis
- 🚨 Fraud Detection
- 👥 Customer Analytics
- 📦 Product Performance
- 📱 Device Analysis
- 📋 Fraud Rule Analysis
- 🌍 Geographic Insights
        """
    )

    st.info(
        """
### 💡 Example Questions

• Total orders today

• Total fraudulent orders

• Fraud rate by state

• Top 10 customers by spending

• Revenue by product category

• Top selling products

• Fraud trend by month

• Orders rejected today

• Top triggered fraud rules

• Fraud orders by device type

• Revenue by city

• Average order value

• High-value fraudulent orders

• Top 10 fraudulent products

• Show all rejected orders
        """
    )

    st.markdown("---")

    with st.sidebar:

        st.markdown("---")
        st.markdown("### ⚙️ Analytics Engine")

        st.caption("**Domain:** E-commerce Fraud Detection")
        st.caption("**Database:** PostgreSQL")
        st.caption("**Schema:** master")
        st.caption("**LLM Provider:** Groq")

        st.caption(f"**SQL Model:** `{GROQ_SQL_MODEL}`")
        st.caption(f"**Repair Model:** `{GROQ_REPAIR_MODEL}`")
        st.caption(f"**Summary Model:** `{GROQ_SUMMARY_MODEL}`")

        st.markdown("---")
        st.markdown("### 🔌 Connection Status")

        if GROQ_API_KEY:
            st.success("✅ Groq Connected")
        else:
            st.error("❌ Groq API Key Missing")

        st.markdown("---")
        st.markdown(f"### 📊 Session Info")
        st.caption(f"Messages in history: {len(st.session_state.messages)}")

        st.markdown("---")

        if st.button(
            "🗑️ Clear Chat History",
            use_container_width=True,
            key="clear_chat_btn",
        ):
            st.session_state.messages = []
            st.rerun()

    # Render chat history
    for idx, msg in enumerate(st.session_state.messages):

        with st.chat_message(msg["role"]):

            st.markdown(msg["content"])

            if msg["role"] == "assistant":

                if msg.get("sql"):
                    with st.expander(
                        "🛠️ View Generated SQL",
                        expanded=False,
                    ):
                        st.code(msg["sql"], language="sql")

                stored_df = msg.get("df")

                if stored_df is not None:

                    try:
                        df_restored = pd.DataFrame(stored_df)
                        df_restored = _restore_dataframe_types(df_restored)

                        if not df_restored.empty:

                            with st.expander(
                                "📋 View Query Result",
                                expanded=False,
                            ):
                                st.dataframe(
                                    df_restored,
                                    use_container_width=True,
                                    key=f"hist_df_{idx}",
                                )

                            _render_chart(df_restored)
                    except Exception as e:
                        st.warning(f"Could not restore dataframe: {str(e)}")

    # User input
    if user_query := st.chat_input(
        "Ask any E-commerce Analytics question..."
    ):

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_query,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_query)

        _run_query_pipeline(user_query)


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    render_chatbot_tab()