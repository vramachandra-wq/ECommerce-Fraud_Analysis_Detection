import re
import logging
import pandas as pd
import streamlit as st
import json

from groq import APIConnectionError
from ai.groq_client import get_groq_client, create_chat_completion
from ai.prompt_constants import (
    GROQ_API_KEY,
    GROQ_INTENT_MODEL,
    GROQ_REPAIR_MODEL,
    GROQ_SQL_MODEL,
    GROQ_SUMMARY_MODEL,
    MAX_HISTORY,
    MAX_STORED_MESSAGES,
    MARKDOWN_PREVIEW_ROWS,
    SCHEMA_CONTEXT,
    SQL_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT_BASE,
    STRATEGY_SUMMARY_PROMPT_BASE,
    REPAIR_PROMPT_TEMPLATE,
    INTENT_SYSTEM_PROMPT,
    ADVISORY_SYSTEM_PROMPT,
    SUMMARY_MAX_TOKENS,
    INTENT_MAX_TOKENS,
    ADVISORY_MAX_TOKENS,
    SQL_MAX_TOKENS,
    REPAIR_MAX_TOKENS,
    INTENT_REASONING_EFFORT,
    ADVISORY_REASONING_EFFORT,
    SQL_REASONING_EFFORT,
    REPAIR_REASONING_EFFORT,
    SUMMARY_REASONING_EFFORT,
    AI_RECOMMENDATION_PROMPT,
    RECOMMENDATION_MAX_TOKENS,
    RECOMMENDATION_REASONING_EFFORT,
)
from database.connection import get_pooled_connection, release_pooled_connection
from database.transaction_repository import log_chatbot_interaction

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
    "email": "email",
    "phone_number": "phone",
    "phone": "phone",
    "mobile": "phone",
    "mobile_number": "phone",
    "address": "address",
    "default_address": "address",
    "ip_address": "ip",
    "password": "secret",
}


def _sensitive_mask_type(column_name: str) -> str | None:
    """Resolve mask type from an exact column name or common PII naming patterns."""
    col = str(column_name).lower().strip()
    if col in SENSITIVE_COLUMNS:
        return SENSITIVE_COLUMNS[col]
    if "email" in col:
        return "email"
    if "phone" in col or "mobile" in col:
        return "phone"
    if "password" in col or col in {"secret", "pwd"}:
        return "secret"
    if "ip_address" in col or col == "ip":
        return "ip"
    if "address" in col:
        return "address"
    return None


PROHIBITED_SQL_COLUMNS = {
    "customers.password",
    "password",
}

_STRATEGY_KEYWORDS = [
    "strateg",       # strategy, strategies, strategic
    "grow", "growth",
    "improve", "improvement",
    "increase", "boost",
    "recommend", "recommendation",
    "how can we", "how do we", "how to",
    "action plan", "plan to",
    "reduce fraud", "reduce risk", "mitigat",
]


def _wants_strategy_answer(user_query: str) -> bool:
    """Detect growth/strategy-style phrasing so the summary step returns
    concrete strategies grounded in the fresh query result, instead of the
    default single-recommendation insight summary."""
    q = user_query.lower()
    return any(kw in q for kw in _STRATEGY_KEYWORDS)


def _extract_sql(text: str) -> str:
    """Extract SQL from the model response.

    Tries in order:
    1. A ```sql ... ``` fenced block (standard output format).
    2. Any generic ``` ... ``` fenced block (model forgot the language tag).
    3. The first SELECT or WITH statement found in the raw text, stripping any
       surrounding prose — prevents raw model chatter from reaching execution.
    """
    # 1. Explicit sql fence
    match = re.search(r"```\s*sql\s*\n(.*?)\n\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. Generic fence (no language tag)
    match = re.search(r"```\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if re.match(r"^\s*(select|with)\b", candidate, re.IGNORECASE):
            return candidate

    # 3. Find first SELECT or WITH in bare text and take everything from there
    match = re.search(r"((?:select|with)\b.*)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: return as-is and let validation catch it
    return text.strip()


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL line (--) and block (/* */) comments before validation/execution.

    LLM-generated SQL frequently includes explanatory comments. Left in, they can:
    (a) break the leading-keyword check when a comment precedes SELECT/WITH, and
    (b) trigger false-positive blocked-keyword hits when a comment happens to
    mention a word like "update" in plain English (e.g. "-- update the fraud
    flag interpretation" contains no UPDATE statement, but the raw-text scan
    would still flag it).
    Comments carry no executable meaning, so they're removed entirely rather
    than special-cased in every individual check.
    """
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    sql = re.sub(r"--[^\n]*", "", sql)                      # line comments
    sql = re.sub(r"\n\s*\n+", "\n", sql)                    # collapse blank lines
    return sql.strip()


def _friendly_error_message(e: Exception, stage: str) -> str:
    """Translate a raw exception into a graceful, user-facing message.

    The person asking a question should never see a stack trace or a raw
    driver/API error string — they should see a plain-English explanation
    and, where possible, a nudge on what to try next. The full technical
    error is still preserved wherever we log to master.ai_chat_logs, so
    nothing is lost for debugging; it's just kept out of the chat UI.

    `stage` identifies where in the pipeline the failure happened
    ("connection", "generation", "repair", "execution", "summary", "chart",
    or "pipeline" for anything uncaught elsewhere) so the fallback copy
    stays relevant even when the exception text itself is unhelpful.
    """
    text = str(e).lower()

    # Cross-cutting checks: these can surface at almost any stage.
    if any(s in text for s in ("connection", "timeout", "timed out", "unreachable", "refused")):
        return "⚠️ I'm having trouble reaching the service right now. Please try again in a moment."

    if any(s in text for s in ("permission denied", "access denied", "not authorized", "unauthorized")):
        return "🔒 I don't have permission to access that data."

    if stage == "execution":
        # Covers missing tables/columns, malformed generated SQL, or any
        # other execution-time failure. The person just wants to know the
        # data isn't available, not see a database driver error.
        return (
            "📭 The data you're requesting isn't available right now. "
            "Try rephrasing your question, or ask about a different metric, "
            "time period, or filter."
        )

    if stage == "generation":
        return "🤔 I couldn't work out how to answer that question. Could you try rephrasing it?"

    if stage == "repair":
        return "🔧 I couldn't automatically fix that query. Try rephrasing your question."

    if stage == "summary":
        return (
            "📝 The data loaded successfully, but I couldn't generate a "
            "written summary this time — you can still explore the results below."
        )

    if stage == "chart":
        return "📊 I couldn't render a chart for this data, but you can still view it in the table below."

    if stage == "recommendations":
        return "💡 Couldn't generate follow-up suggestions this time, but your results above are unaffected."

    return "⚠️ Something went wrong while processing your request. Please try again or rephrase your question."


def _extract_usage(completion) -> tuple[int, int]:
    """Pull (input_tokens, output_tokens) off a Groq completion's usage block.

    Groq's response mirrors the OpenAI schema (usage.prompt_tokens /
    usage.completion_tokens). Returns (0, 0) if usage is missing so callers
    never have to special-case a malformed or absent usage object.
    """
    usage = getattr(completion, "usage", None)
    if not usage:
        return 0, 0
    return (
        getattr(usage, "prompt_tokens", 0) or 0,
        getattr(usage, "completion_tokens", 0) or 0,
    )


def _classify_intent(client, user_query: str, history: list[dict]) -> tuple[str, int, int]:
    """Classify user_query as NEW_QUERY, FOLLOWUP_QUERY, or GENERAL.

    Returns (label, input_tokens, output_tokens). Defaults to "NEW_QUERY" (the
    safest fallback — it just means the question runs standalone through SQL
    generation, which is where the pipeline already spent most of its time
    before this classifier existed) on any classification failure or
    unrecognized output.
    """
    if not history:
        return "NEW_QUERY", 0, 0

    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}" for m in history
    )

    try:
        completion = create_chat_completion(
            client,
            model=GROQ_INTENT_MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Conversation history:\n{transcript}\n\nLatest question:\n{user_query}",
                },
            ],
            temperature=0.0,
            max_tokens=INTENT_MAX_TOKENS,
            reasoning_effort=INTENT_REASONING_EFFORT,
            include_reasoning=False,
        )
        label = (completion.choices[0].message.content or "").strip().upper()
        in_tok, out_tok = _extract_usage(completion)
        if "GENERAL" in label:
            return "GENERAL", in_tok, out_tok
        if "FOLLOWUP" in label:
            return "FOLLOWUP_QUERY", in_tok, out_tok
        return "NEW_QUERY", in_tok, out_tok
    except Exception:
        # If classification fails for any reason, fall back to treating the
        # query as a standalone data question rather than blocking the pipeline.
        return "NEW_QUERY", 0, 0


def _get_last_result_context(history: list[dict]) -> str:
    """Return the most recently stored result table in history as markdown.

    Used to ground GENERAL (advisory/strategy) answers in the actual numbers
    from the last data query, instead of letting the model improvise figures.
    Returns an empty string if no prior result table is available.
    """
    for msg in reversed(history):
        if msg.get("role") != "assistant" or not msg.get("df"):
            continue
        try:
            df = pd.DataFrame(msg["df"])
            df = _restore_dataframe_types(df)
            df = sanitize_dataframe_for_llm(df)
            if not df.empty:
                return dataframe_to_markdown(df, max_rows=MARKDOWN_PREVIEW_ROWS)
        except Exception:
            continue
    return ""


def _get_followup_context(history: list[dict]) -> str:
    """
    Builds structured context for follow-up questions.
    Gives the LLM the previous SQL, returned columns and a small sample.

    NOTE: history here is recent_messages which already excludes the current
    user turn (it's built from st.session_state.messages BEFORE the new
    message is appended). So the most recent user message in history IS the
    previous question, which is exactly what we want.
    """

    previous_user = None
    previous_sql = None
    previous_df = None

    for msg in reversed(history):
        if previous_df is None and msg.get("role") == "assistant":
            if msg.get("df"):
                previous_df = pd.DataFrame(msg["df"])
            if msg.get("sql"):
                previous_sql = msg["sql"]

        if previous_user is None and msg.get("role") == "user":
            previous_user = msg["content"]

        if previous_user and previous_sql and previous_df is not None:
            break

    if previous_df is None or previous_sql is None:
        return ""

    previous_df = _restore_dataframe_types(previous_df)

    return f"""
PREVIOUS USER QUESTION:
{previous_user}

PREVIOUS SQL QUERY:
{previous_sql}

RETURNED COLUMNS:
{", ".join(previous_df.columns)}

SAMPLE RESULT (first 3 rows — full dataset is larger):
{dataframe_to_markdown(previous_df.head(3))}
"""

# def _detect_analysis_context(
#     user_query: str,
#     sql_query: str,
#     result_df: pd.DataFrame,
#     assistant_summary: str,
# ) -> dict:
#     """
#     Detect the business domains involved in the current analysis.

#     Returns:
#         {
#             "fraud": True,
#             "customer": False,
#             "product": True,
#             ...
#         }
#     """

#     combined_text = " ".join([
#         user_query.lower(),
#         sql_query.lower(),
#         assistant_summary.lower(),
#         " ".join(result_df.columns.astype(str).str.lower())
#     ])

#     topics = {
#         "fraud": [
#             "fraud",
#             "rejected",
#             "flagged",
#             "risk",
#             "is_fraud",
#             "rule",
#             "review"
#         ],

#         "customer": [
#             "customer",
#             "user",
#             "customer_name",
#             "email",
#             "phone"
#         ],

#         "product": [
#             "product",
#             "category",
#             "item"
#         ],

#         "geography": [
#             "city",
#             "state",
#             "country",
#             "zip"
#         ],

#         "device": [
#             "device",
#             "ip",
#             "browser"
#         ],

#         "revenue": [
#             "amount",
#             "revenue",
#             "sales",
#             "price"
#         ],

#         "order": [
#             "order",
#             "approved",
#             "quantity"
#         ]
#     }

#     detected = {}

#     for topic, keywords in topics.items():
#         detected[topic] = any(
#             word in combined_text
#             for word in keywords
#         )

#     return detected

# def _generate_recommendations(context: dict) -> dict:
#     """
#     Generate follow-up questions, business advisories,
#     and related analytical questions based on the detected context.
#     """

#     recommendations = {
#         "followups": [],
#         "advisories": [],
#         "explore": []
#     }

#     if context.get("fraud"):
#         recommendations["followups"].extend([
#             "Which products have the highest fraud rate?",
#             "Which customers are repeatedly involved in fraudulent transactions?",
#             "Show fraud trends over time.",
#             "Which fraud rules are triggered most frequently?",
#             "Which states have the highest fraud percentage?"
#         ])

#         recommendations["advisories"].extend([
#             "Monitor repeat fraudulent customers.",
#             "Review fraud rules with the highest trigger frequency.",
#             "Strengthen verification for high-value transactions.",
#             "Investigate regions with abnormal fraud activity."
#         ])

#         recommendations["explore"].extend([
#             "Analyze fraud by device.",
#             "Compare fraud across product categories."
#         ])

#     if context.get("customer"):
#         recommendations["followups"].extend([
#             "Who are the top spending customers?",
#             "Which customers have the highest rejection rate?",
#             "Show customer purchases by state.",
#             "Which customers place the most orders?"
#         ])

#         recommendations["advisories"].extend([
#             "Identify high-value customers for retention.",
#             "Review customers with frequent rejected orders."
#         ])

#     if context.get("product"):
#         recommendations["followups"].extend([
#             "Which products generate the highest revenue?",
#             "Which products have the highest fraud rate?",
#             "Compare product category performance.",
#             "Show monthly sales by product."
#         ])

#         recommendations["advisories"].extend([
#             "Review products with increasing fraud trends.",
#             "Monitor low-performing products."
#         ])

#     if context.get("geography"):
#         recommendations["followups"].extend([
#             "Compare fraud across states.",
#             "Which cities generate the highest revenue?",
#             "Show approval rate by region."
#         ])

#         recommendations["advisories"].extend([
#             "Focus fraud monitoring in high-risk regions.",
#             "Compare approval rates across locations."
#         ])

#     if context.get("device"):
#         recommendations["followups"].extend([
#             "Which devices are linked to the most fraud?",
#             "Compare fraud by device type."
#         ])

#         recommendations["advisories"].extend([
#             "Monitor devices associated with repeated fraud."
#         ])

#     if context.get("revenue"):
#         recommendations["followups"].extend([
#             "Show monthly revenue trend.",
#             "Which products contribute the most revenue?",
#             "Compare revenue across categories."
#         ])

#         recommendations["advisories"].extend([
#             "Monitor revenue fluctuations.",
#             "Review declining product performance."
#         ])

#     # Remove duplicates while preserving order
#     recommendations["followups"] = list(dict.fromkeys(recommendations["followups"]))
#     recommendations["advisories"] = list(dict.fromkeys(recommendations["advisories"]))
#     recommendations["explore"] = list(dict.fromkeys(recommendations["explore"]))

#     return recommendations

# def _render_recommendations(recommendations: dict):
#     """
#     Render AI-powered follow-up questions and business recommendations.
#     """

#     st.markdown("---")
#     st.markdown("## 🤖 AI Recommendations")

    # ----------------------------
    # Follow-up Questions
    # ----------------------------

    # # for idx, msg in enumerate(st.session_state.messages):
    # #     with st.chat_message(msg["role"]):

    # #         st.markdown(msg["content"])


    # #         followups = msg.get("followups", [])

    # #         if followups:
    # #             with st.expander("🔍 Suggested Follow-up Questions", expanded=True):
    # #                 for i, question in enumerate(followups):

    # #                     if st.button(
    # #                         f"💡 {question}",
    # #                         key=f"followup_{idx}_{i}",
    # #                         use_container_width=True,
    # #                     ):
    # #                         st.session_state.selected_followup = question
    # #                         st.rerun()
    #         # for question in followups[:5]:
    #         #     st.markdown(f"• {question}")

    # # ----------------------------
    # # Business Advisories
    # # ----------------------------
    # advisories = recommendations.get("advisories", [])

    # if advisories:
    #     with st.expander("💡 Business Advisory", expanded=False):
    #         for advice in advisories[:4]:
    #             st.markdown(f"• {advice}")

    # # ----------------------------
    # # Explore More
    # # ----------------------------
    # explore = recommendations.get("explore", [])

    # if explore:
    #     with st.expander("📈 Explore More", expanded=False):
    #         for item in explore[:3]:
    #             st.markdown(f"• {item}")   

def _generate_ai_recommendations(
    client,
    user_query: str,
    sql_query: str,
    sanitized_df: pd.DataFrame,
    executive_summary: str,
    conversation_history: str,
) -> dict:
    """
    Generate AI-powered follow-up questions and business advice.
    """

    data_preview = dataframe_to_markdown(sanitized_df, max_rows=MARKDOWN_PREVIEW_ROWS)

    prompt = AI_RECOMMENDATION_PROMPT.format(
        user_query=user_query,
        sql_query=sql_query,
        summary=executive_summary,
        conversation_history=conversation_history,
        data_preview=data_preview,
    )

    try:

        completion = create_chat_completion(
            client=client,
            model=GROQ_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                }
            ],
            temperature=0.3,
            max_tokens=RECOMMENDATION_MAX_TOKENS,
            reasoning_effort=RECOMMENDATION_REASONING_EFFORT,
            include_reasoning=False,
        )

        response = completion.choices[0].message.content.strip()

        # Model sometimes wraps the JSON in ```json fences or adds stray
        # text despite instructions — strip fences and extract the {...}
        # block so json.loads doesn't fail and silently fall back to empty.
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", response, re.DOTALL)
        if fence_match:
            response = fence_match.group(1).strip()

        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            response = brace_match.group(0)

        recommendations = json.loads(response)

        recommendations.setdefault("followups", [])
        recommendations.setdefault("business_advice", [])

        return recommendations

    except Exception as e:
        logging.exception("AI recommendation generation failed")
        # Avoid Streamlit UI calls here so the same helper works for the
        # headless portal API (ai/chat_api.py) as well as Streamlit.
        return {
            "followups": [],
            "business_advice": [],
        }

def _validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query with comprehensive checks.

    The join-duplicate check strips CTE definitions before scanning so that
    a table referenced inside a CTE body AND again in the outer query is not
    incorrectly flagged. Complex analytics queries (e.g. fraud-rate CTEs that
    reference orders twice across separate CTE legs) were previously triggering
    false-positive validation failures.
    """
    sql = _strip_sql_comments(sql)
    sql_lower = sql.lower().strip()

    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        return False, "Only SELECT queries are permitted."

    for kw in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql_lower):
            return False, f"Blocked keyword detected: `{kw.upper()}`."

    for col in PROHIBITED_SQL_COLUMNS:
        if re.search(rf"\b{re.escape(col.lower())}\b", sql_lower):
            return False, f"Query may not select prohibited column: `{col}`."

    # NOTE: email/phone_number are intentionally NOT blocked here.
    # They may be selected, but values are masked before LLM prompts and
    # before any UI result table/chart display (see sanitize_dataframe_for_llm).
    # Only truly forbidden columns are blocked below.

    # For the duplicate-join check, only inspect the outer query — strip CTE
    # bodies so joins inside CTEs don't inflate the count for the outer query.
    # Strategy: remove everything between the outermost WITH ... AS (...) pairs
    # before scanning JOIN/FROM references.
    scan_target = sql_lower
    if scan_target.startswith("with"):
        # Find the final SELECT that follows all CTE definitions
        final_select = re.search(r'\)\s*(select\b)', scan_target, re.IGNORECASE)
        if final_select:
            scan_target = scan_target[final_select.start(1):]

    join_pattern = re.compile(
        r"(?:JOIN|FROM)\s+(?:master\.)?(\w+)",
        re.IGNORECASE,
    )

    table_counts = {}
    for tbl in join_pattern.findall(scan_target):
        table_counts[tbl] = table_counts.get(tbl, 0) + 1

    for dim in _KNOWN_DIMENSION_TABLES:
        if table_counts.get(dim, 0) > 1:
            return (
                False,
                f"Table `{dim}` is joined multiple times. Use aliases or a CTE."
            )

    return True, ""


def _repair_sql(sql: str, error: str) -> tuple[str, int, int]:
    """Attempt to repair invalid SQL using Groq. Returns (sql, input_tokens, output_tokens)."""
    client = get_groq_client()
    if not client:
        st.warning("⚠️ Groq client unavailable. Cannot repair SQL.")
        return sql, 0, 0

    repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
        error=error,
        schema=SCHEMA_CONTEXT,
        sql=sql,
    )

    try:
        response = create_chat_completion(
            client,
            model=GROQ_REPAIR_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": repair_prompt,
                }
            ],
            temperature=0,
            max_tokens=REPAIR_MAX_TOKENS,
            reasoning_effort=REPAIR_REASONING_EFFORT,
            include_reasoning=False,
        )
        in_tok, out_tok = _extract_usage(response)
        return _extract_sql(response.choices[0].message.content or ""), in_tok, out_tok
    except Exception as e:
        st.warning(_friendly_error_message(e, "repair"))
        return sql, 0, 0


def _restore_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Restore datetime and numeric types after deserialization."""
    for col in df.columns:
        col_lower = col.lower()
        if 'timestamp' in col_lower or 'date' in col_lower or '_at' in col_lower:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except (ValueError, TypeError):
                pass
        elif 'amount' in col_lower or 'price' in col_lower or 'value' in col_lower:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except (ValueError, TypeError):
                pass
    return df

def _mask_email(value):
    if pd.isna(value):
        return value

    value = str(value)

    if "@" not in value:
        return value

    name, domain = value.split("@", 1)

    if len(name) <= 1:
        masked = "*"
    else:
        masked = name[0] + "*" * (len(name) - 1)

    return f"{masked}@{domain}"

def _mask_phone(value):
    if pd.isna(value):
        return value

    value = str(value)

    if len(value) <= 4:
        return value

    return "*" * (len(value) - 4) + value[-4:]

def _mask_address(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    if len(value) <= 6:
        return "***"
    return value[:4] + "***" + value[-2:]

def _mask_ip(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    parts = value.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    if len(value) <= 4:
        return "***"
    return value[:4] + "***"

def _mask_value(column_name, value):
    mask_type = _sensitive_mask_type(column_name)

    if mask_type == "email":
        return _mask_email(value)

    if mask_type == "phone":
        return _mask_phone(value)

    if mask_type == "address":
        return _mask_address(value)

    if mask_type == "ip":
        return _mask_ip(value)

    if mask_type == "secret":
        return "********" if not pd.isna(value) else value

    return value

def sanitize_dataframe_for_llm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a dataframe with PII columns masked for LLM prompts and UI display.
    """

    sanitized_df = df.copy()

    for column in sanitized_df.columns:
        if _sensitive_mask_type(column):
            sanitized_df[column] = sanitized_df[column].apply(
                lambda value, col=column: _mask_value(col, value)
            )

    return sanitized_df


# Alias kept for tests / older call sites.
mask_sensitive_dataframe = sanitize_dataframe_for_llm


def dataframe_to_markdown(df: pd.DataFrame, *, max_rows: int | None = None) -> str:
    """Render a DataFrame as markdown with a safe fallback when tabulate is missing."""
    if df is None or df.empty:
        return "(empty result)"
    preview = df if max_rows is None else df.head(max_rows)
    try:
        return preview.to_markdown(index=False)
    except ImportError:
        return preview.to_string(index=False)
    except Exception:
        return preview.to_string(index=False)

def _get_best_axis(df: pd.DataFrame, cols_list: list, priority_patterns: list) -> str | None:
    """Select best axis column based on priority patterns."""
    if not cols_list:
        return None
    for pattern in priority_patterns:
        for col in cols_list:
            if pattern.lower() in col.lower():
                return col
    return cols_list[0]


def _detect_chart_columns(df: pd.DataFrame):
    """
    Automatically detect the best X and Y columns for visualization.
    """

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    object_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    if not numeric_cols:
        return None, None

    y_axis = (
        _get_best_axis(df, numeric_cols, ["count", "amount", "total", "value"])
        or numeric_cols[0]
    )

    if datetime_cols:
        x_axis = (
            _get_best_axis(df, datetime_cols, ["timestamp", "date", "created"])
            or datetime_cols[0]
        )
    elif object_cols:
        x_axis = (
            _get_best_axis(df, object_cols, ["status", "category", "type", "name"])
            or object_cols[0]
        )
    else:
        x_axis = numeric_cols[0]

    return x_axis, y_axis

def _render_chart(df: pd.DataFrame, chart_key: str = "live") -> None:
    """
    Interactive chart renderer.

    Features
    --------
    • Auto chart selection
    • Manual chart selection
    • X-Axis selection
    • Y-Axis selection
    • Horizontal bar chart
    • Line chart
    • Area chart
    • Pie chart
    • Scatter chart
    • Table only option

    No SQL is re-executed.
    Everything works on the existing dataframe.
    """

    if df.empty:
        return

    if len(df.columns) < 2:
        st.info("Not enough columns available to visualize.")
        return

    df = _restore_dataframe_types(df.copy())

    numeric_cols = (
        df.select_dtypes(include="number")
        .columns
        .tolist()
    )

    datetime_cols = (
        df.select_dtypes(include=["datetime64"])
        .columns
        .tolist()
    )

    category_cols = (
        df.select_dtypes(
            include=[
                "object",
                "category",
                "bool",
            ]
        )
        .columns
        .tolist()
    )

    if not numeric_cols:
        st.info("No numeric columns available for charting.")
        return

    auto_x, auto_y = _detect_chart_columns(df)

    st.markdown("---")
    st.markdown("## 📊 Visualization")

    control_col1, control_col2, control_col3 = st.columns(3)

    with control_col1:

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Auto",
                "Bar Chart",
                "Horizontal Bar",
                "Line Chart",
                "Area Chart",
                "Pie Chart",
                "Scatter Plot",
                "Table Only",
            ],
            key=f"chart_type_{chart_key}",
        )

    available_x = []

    if datetime_cols:
        available_x.extend(datetime_cols)

    if category_cols:
        available_x.extend(category_cols)

    if not available_x:
        available_x.extend(numeric_cols)

    with control_col2:

        x_axis = st.selectbox(
            "X Axis",
            available_x,
            index=available_x.index(auto_x)
            if auto_x in available_x
            else 0,
            key=f"x_axis_{chart_key}",
        )

    with control_col3:

        y_axis = st.selectbox(
            "Y Axis",
            numeric_cols,
            index=numeric_cols.index(auto_y)
            if auto_y in numeric_cols
            else 0,
            key=f"y_axis_{chart_key}",
        )

    chart_df = df.copy()

    if chart_type == "Table Only":
        return

    if chart_type == "Auto":

        if datetime_cols:
            chart_type = "Line Chart"

        elif category_cols:

            if chart_df[x_axis].nunique() <= 5:
                chart_type = "Pie Chart"

            else:
                chart_type = "Bar Chart"

        else:
            chart_type = "Scatter Plot"

    st.caption(f"Current Visualization: **{chart_type}**")

    # ==========================================================
    # BAR CHART
    # ==========================================================

    if chart_type == "Bar Chart":

        try:

            plot_df = (
                chart_df[[x_axis, y_axis]]
                .sort_values(y_axis, ascending=False)
                .set_index(x_axis)
            )

            st.bar_chart(
                plot_df,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return


    # ==========================================================
    # HORIZONTAL BAR CHART
    # ==========================================================

    if chart_type == "Horizontal Bar":

        try:

            import plotly.express as px

            plot_df = (
                chart_df[[x_axis, y_axis]]
                .sort_values(y_axis)
            )

            fig = px.bar(
                plot_df,
                x=y_axis,
                y=x_axis,
                orientation="h",
                text_auto=True,
            )

            fig.update_layout(
                height=500,
                yaxis_title=x_axis,
                xaxis_title=y_axis,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return


    # ==========================================================
    # LINE CHART
    # ==========================================================

    if chart_type == "Line Chart":

        try:

            plot_df = (
                chart_df[[x_axis, y_axis]]
                .sort_values(x_axis)
                .set_index(x_axis)
            )

            st.line_chart(
                plot_df,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return


    # ==========================================================
    # AREA CHART
    # ==========================================================

    if chart_type == "Area Chart":

        try:

            plot_df = (
                chart_df[[x_axis, y_axis]]
                .sort_values(x_axis)
                .set_index(x_axis)
            )

            st.area_chart(
                plot_df,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return


    # ==========================================================
    # PIE CHART
    # ==========================================================

    if chart_type == "Pie Chart":

        try:

            import plotly.express as px

            pie_df = chart_df[[x_axis, y_axis]]

            fig = px.pie(
                pie_df,
                names=x_axis,
                values=y_axis,
                hole=0.45,
            )

            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            fig.update_layout(
                height=500,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return

    # ==========================================================
    # SCATTER PLOT
    # ==========================================================

    if chart_type == "Scatter Plot":

        try:

            if len(numeric_cols) < 2:
                st.info("Scatter plot requires at least two numeric columns.")
                return

            x_numeric = st.selectbox(
                "Scatter X Axis",
                numeric_cols,
                index=0,
                key=f"scatter_x_{chart_key}",
            )

            y_numeric = st.selectbox(
                "Scatter Y Axis",
                numeric_cols,
                index=1 if len(numeric_cols) > 1 else 0,
                key=f"scatter_y_{chart_key}",
            )

            st.scatter_chart(
                chart_df,
                x=x_numeric,
                y=y_numeric,
                use_container_width=True,
            )

        except Exception as e:

            st.warning(_friendly_error_message(e, "chart"))

        return


    # ==========================================================
    # FALLBACK
    # ==========================================================

    try:

        plot_df = chart_df[[x_axis, y_axis]].set_index(x_axis)

        st.bar_chart(
            plot_df,
            use_container_width=True,
        )

    except Exception as e:

        st.warning(_friendly_error_message(e, "chart"))

    st.markdown("---")

    with st.expander("📊 Visualization Information", expanded=False):

        st.markdown(
            f"""
**Chart Type:** {chart_type}

**Rows Displayed:** {len(chart_df)}

**Columns Available:** {len(chart_df.columns)}

**Selected X Axis:** `{x_axis}`

**Selected Y Axis:** `{y_axis}`
"""
        )


def _run_query_pipeline(user_query: str) -> None:
    client = get_groq_client()
    if not client:
        st.error("🔑 Groq API key missing — add `GROQ_API_KEY` to your `.env` file.")
        return

    recent_messages = st.session_state.messages[:-1][-MAX_HISTORY:]
    total_input_tokens = 0
    total_output_tokens = 0

    with st.chat_message("assistant"):
        with st.status("Processing Analytics Request…", expanded=True) as status:
            sql_query: str | None = None
            try:
                status.write("🔍 Checking conversation context…")
                intent, in_tok, out_tok = _classify_intent(client, user_query, recent_messages)
                total_input_tokens += in_tok
                total_output_tokens += out_tok

                if intent == "GENERAL":
                    status.write("💬 Detected advisory question — answering from prior context, no new query needed")
                    transcript = "\n".join(
                        f"{m['role'].upper()}: {m['content']}" for m in recent_messages
                    )
                    data_context = _get_last_result_context(recent_messages)

                    try:
                        advisory_messages = [{
                            "role": "system",
                            "content": ADVISORY_SYSTEM_PROMPT.format(
                                conversation_context=transcript or "(no prior conversation)",
                                data_context=data_context or "(no prior data table available)",
                                user_query=user_query,
                            ),
                        }]
                        advisory_completion = create_chat_completion(
                            client,
                            model=GROQ_SUMMARY_MODEL,
                            messages=advisory_messages,
                            temperature=0.4,
                            max_tokens=ADVISORY_MAX_TOKENS,
                            reasoning_effort=ADVISORY_REASONING_EFFORT,
                            include_reasoning=False,
                        )
                        advisory_answer = advisory_completion.choices[0].message.content or ""
                        in_tok, out_tok = _extract_usage(advisory_completion)
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok
                        if getattr(advisory_completion.choices[0], "finish_reason", None) == "length":
                            # Ran out of tokens mid-answer — retry once with a
                            # larger budget rather than showing a cut-off answer.
                            advisory_completion = create_chat_completion(
                                client,
                                model=GROQ_SUMMARY_MODEL,
                                messages=advisory_messages,
                                temperature=0.4,
                                max_tokens=ADVISORY_MAX_TOKENS * 2,
                                reasoning_effort=ADVISORY_REASONING_EFFORT,
                                include_reasoning=False,
                            )
                            advisory_answer = advisory_completion.choices[0].message.content or ""
                            in_tok, out_tok = _extract_usage(advisory_completion)
                            total_input_tokens += in_tok
                            total_output_tokens += out_tok

                        if not advisory_answer.strip():
                            advisory_answer = (
                                "I wasn't able to generate a written answer for that this time. "
                                "Could you try rephrasing the question?"
                            )
                    except Exception as e:
                        status.update(label="❌ Could not generate answer", state="complete", expanded=False)
                        friendly = _friendly_error_message(e, "summary")
                        st.error(friendly)
                        log_chatbot_interaction(
                            user_query,
                            None,
                            None,
                            f"ADVISORY_ERROR: {str(e)}",
                            input_tokens=total_input_tokens,
                            output_tokens=total_output_tokens,
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": friendly, "sql": None, "df": None}
                        )
                        return

                    status.update(label="✅ Answer ready", state="complete", expanded=False)
                    st.markdown(advisory_answer)

                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        advisory_answer,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": advisory_answer,
                        "sql": None,
                        "df": None,
                    })
                    if len(st.session_state.messages) > MAX_STORED_MESSAGES:
                        st.session_state.messages = st.session_state.messages[-MAX_STORED_MESSAGES:]
                    return

                llm_payload = [
                    {
                        "role": "system",
                        "content": SQL_SYSTEM_PROMPT,
                    }
                ]

                if intent == "FOLLOWUP_QUERY":
                    status.write("↪ Detected follow-up question — using previous query context")

                    followup_context = _get_followup_context(recent_messages)

                    if followup_context:
                        llm_payload.append({
                            "role": "user",
                            "content": f"""This is a follow-up question. Use the context below to understand what the user is referring to, then write a new SQL query that answers their follow-up.

{followup_context}

FOLLOW-UP RULES:
- Modify the previous SQL to answer the follow-up rather than writing a completely unrelated query.
- Keep the same analytical intent and only change the part the user is asking about (e.g. a different city, date range, filter, or aggregation level).
- If the user uses pronouns ("those", "them", "it", "that"), resolve them from the previous question and result above.
- Do NOT copy the previous SQL verbatim — adapt it to the new question.
- Always apply LIMIT unless the question asks for all records.

The user's follow-up question is below. Respond with ONLY the SQL query.""",
                        })

                else:
                    status.write("🆕 Detected new question — starting fresh")

                llm_payload.append({
                    "role": "user",
                    "content": user_query,
                })

                status.write("🧠 Generating SQL query…")
                try:
                    completion = create_chat_completion(
                        client,
                        model=GROQ_SQL_MODEL,
                        messages=llm_payload,
                        temperature=0.0,
                        max_tokens=SQL_MAX_TOKENS,
                        reasoning_effort=SQL_REASONING_EFFORT,
                        include_reasoning=False,
                    )
                    sql_query = _extract_sql(completion.choices[0].message.content or "")
                    in_tok, out_tok = _extract_usage(completion)
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok
                except APIConnectionError as e:
                    status.update(label="❌ Connection issue", state="complete", expanded=False)
                    friendly = _friendly_error_message(e, "connection")
                    st.error(friendly)
                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        f"CONNECTION_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": friendly, "sql": None, "df": None}
                    )
                    return
                except Exception as e:
                    status.update(label="❌ Could not generate query", state="complete", expanded=False)
                    friendly = _friendly_error_message(e, "generation")
                    st.error(friendly)
                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        f"GENERATION_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": friendly, "sql": None, "df": None}
                    )
                    return

                is_valid, validation_error = _validate_sql(sql_query)
                if is_valid:
                    sql_query = _strip_sql_comments(sql_query)
                else:
                    status.write("🔧 Attempting query repair…")
                    repaired, repair_in_tok, repair_out_tok = _repair_sql(sql_query, validation_error)
                    total_input_tokens += repair_in_tok
                    total_output_tokens += repair_out_tok
                    repaired_valid, repaired_error = _validate_sql(repaired)
                    if repaired_valid:
                        sql_query = _strip_sql_comments(repaired)
                        status.write("✅ Query repaired successfully")
                    else:
                        status.update(label="⚠️ Query validation failed", state="complete", expanded=False)
                        st.error(validation_error)
                        log_chatbot_interaction(
                            user_query,
                            sql_query,
                            None,
                            f"BLOCKED: {validation_error}",
                            input_tokens=total_input_tokens,
                            output_tokens=total_output_tokens,
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": f"⚠️ {validation_error}", "sql": sql_query, "df": None}
                        )
                        return

                status.write("🗄️ Executing query against database…")
                conn = None
                try:
                    conn = get_pooled_connection()
                    result_df = pd.read_sql_query(sql_query, conn)
                except Exception as e:
                    status.update(label="❌ Data not available", state="complete", expanded=False)
                    friendly = _friendly_error_message(e, "execution")
                    st.error(friendly)
                    log_chatbot_interaction(
                        user_query,
                        sql_query,
                        None,
                        f"DB_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": friendly, "sql": sql_query, "df": None}
                    )
                    return
                finally:
                    if conn:
                        release_pooled_connection(conn)

                if result_df.empty:
                    status.update(label="⚠️ No matching data", state="complete", expanded=False)
                    msg = (
                        "📭 No matching data found for your question. Try rephrasing it, "
                        "or ask about a different metric, time period, or filter."
                    )
                    st.info(msg)
                    log_chatbot_interaction(
                        user_query,
                        sql_query,
                        None,
                        "The query executed successfully but returned no matching rows.",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": msg, "sql": sql_query, "df": None}
                    )
                    return

                result_df = _restore_dataframe_types(result_df)
                # Sanitize dataframe before sending it to any LLM
                sanitized_df = sanitize_dataframe_for_llm(result_df)
                strategy_mode = _wants_strategy_answer(user_query)
                summary_prompt_template = (
                    STRATEGY_SUMMARY_PROMPT_BASE if strategy_mode else SUMMARY_SYSTEM_PROMPT_BASE
                )
                status.write(
                    "🚀 Turning results into growth strategies…" if strategy_mode
                    else "📝 Generating executive insight summary…"
                )
                data_preview = dataframe_to_markdown(sanitized_df, max_rows=MARKDOWN_PREVIEW_ROWS)

                try:
                    summary_completion = create_chat_completion(
                        client,
                        model=GROQ_SUMMARY_MODEL,
                        messages=[{
                            "role": "system",
                            "content": summary_prompt_template.format(
                                user_query=user_query,
                                data_preview=data_preview,
                            ),
                        }],
                        temperature=0.3,
                        max_tokens=SUMMARY_MAX_TOKENS,
                        reasoning_effort=SUMMARY_REASONING_EFFORT,
                        include_reasoning=False,
                    )
                    assistant_summary = summary_completion.choices[0].message.content or ""
                    in_tok, out_tok = _extract_usage(summary_completion)
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok
                    finish_reason = getattr(
                        summary_completion.choices[0], "finish_reason", None
                    )
                    if finish_reason == "length" or not assistant_summary.strip():
                        # Ran out of tokens mid-summary (or reasoning ate the
                        # whole budget) — retry once with a larger budget
                        # rather than showing a cut-off/blank answer.
                        summary_completion = create_chat_completion(
                            client,
                            model=GROQ_SUMMARY_MODEL,
                            messages=[{
                                "role": "system",
                                "content": summary_prompt_template.format(
                                    user_query=user_query,
                                    data_preview=data_preview,
                                ),
                            }],
                            temperature=0.3,
                            max_tokens=SUMMARY_MAX_TOKENS * 2,
                            reasoning_effort=SUMMARY_REASONING_EFFORT,
                            include_reasoning=False,
                        )
                        assistant_summary = summary_completion.choices[0].message.content or ""
                        in_tok, out_tok = _extract_usage(summary_completion)
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok

                    if not assistant_summary.strip():
                        assistant_summary = "Unable to generate a written summary. Please review the data below."
                except Exception as e:
                    st.warning(_friendly_error_message(e, "summary"))
                    assistant_summary = "Unable to generate a written summary. Please review the data below."

                status.update(label="✅ Analysis completed", state="complete", expanded=False)
                with st.expander("📋 View Result Data", expanded=False):
                    st.dataframe(sanitized_df, use_container_width=True)

                _render_chart(sanitized_df, chart_key=f"live_{len(st.session_state.messages)}")
                st.markdown("### 🚀 Growth Strategies" if strategy_mode else "### 📋 Key Insights")
                st.markdown(assistant_summary)

                # ============================================================
                # AI Recommendation Engine
                # ============================================================

                conversation_history = "\n".join(
                    f"{m['role'].upper()}: {m['content']}" for m in recent_messages
                )
                recommendations = _generate_ai_recommendations(
                    client=client,
                    user_query=user_query,
                    sql_query=sql_query,
                    sanitized_df=sanitized_df,
                    executive_summary=assistant_summary,
                    conversation_history=conversation_history,
                )

                if recommendations["business_advice"]:
                    st.markdown("##### 📈 Business Advice")
                    for advice in recommendations["business_advice"]:
                        st.markdown(f"• {advice}")

                if recommendations["followups"]:
                    st.markdown("##### 💡 Suggested Questions")
                    for i, question in enumerate(recommendations["followups"]):
                        if st.button(
                            f"💡 {question}",
                            key=f"followup_live_{len(st.session_state.messages)}_{i}",
                            use_container_width=True,
                        ):
                            st.session_state.selected_followup = question
                            st.rerun()

                log_chatbot_interaction(
                    user_query,
                    sql_query,
                    result_df,
                    assistant_summary,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_summary,
                    "sql": sql_query,
                    "df": sanitized_df.to_dict(orient="records"),
                    "followups": recommendations["followups"],
                    "business_advice": recommendations["business_advice"],
                })

                if len(st.session_state.messages) > MAX_STORED_MESSAGES:
                    st.session_state.messages = st.session_state.messages[-MAX_STORED_MESSAGES:]

            except Exception as e:
                status.update(label="❌ Pipeline error", state="complete", expanded=False)
                err_msg = _friendly_error_message(e, "pipeline")
                st.exception(e)
                st.error(err_msg)
                log_chatbot_interaction(
                    user_query,
                    sql_query,
                    None,
                    str(e),
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": err_msg, "sql": sql_query, "df": None}
                )


def render_chatbot_tab() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.header("🛒 E-commerce Fraud Detection Analytics Chatbot")

    st.markdown(
        """
Ask questions about:

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

• Total fraudulent orders

• Fraud rate by state

• Top 10 customers by spending

• Revenue by product category

• Top selling products

• Fraud orders by device type

• Revenue by city
        """
    )

    st.markdown("---")

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔌 Connection Status")

        if GROQ_API_KEY:
            st.success("✅ Groq Connected")
        else:
            st.error("❌ Groq API Key Missing")

        if st.button(
            "🗑️ Clear Chat History",
            use_container_width=True,
            key="clear_chat_btn",
        ):
            st.session_state.messages = []
            st.rerun()


    # =====================================================
    # Chat History
    # =====================================================

    for idx, msg in enumerate(st.session_state.messages):

        with st.chat_message(msg["role"]):

            st.markdown(msg["content"])

            # Suggested Follow-up Questions
            followups = msg.get("followups", [])

            if followups:

                st.markdown("##### 💡 Suggested Questions")

                for i, question in enumerate(followups):

                    if st.button(
                        f"💡 {question}",
                        key=f"followup_{idx}_{i}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_followup = question
                        st.rerun()

            # Business Advice
            business_advice = msg.get("business_advice", [])

            if business_advice:

                st.markdown("##### 📈 Business Advice")

                for advice in business_advice:
                    st.markdown(f"• {advice}")

            # Restore DataFrame
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

                        _render_chart(
                            df_restored,
                            chart_key=f"hist_{idx}",
                        )

                except Exception:

                    logging.exception(
                        "Failed to reload stored results for history message idx=%s",
                        idx,
                    )

                    st.warning(
                        "📋 Couldn't reload the saved results for this message."
                    )
    # ---------------------------------------------------------
# Handle Follow-up Button Click or Manual Chat Input
# ---------------------------------------------------------

    if "selected_followup" in st.session_state:

        user_query = st.session_state.pop("selected_followup", None)
        if user_query is None:
            user_query = st.chat_input(
                "Ask any E-commerce Analytics question..."
            )

    else:
        user_query = st.chat_input(
            "Ask any E-commerce Analytics question..."
        )



    if user_query:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_query,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_query)

        _run_query_pipeline(user_query)