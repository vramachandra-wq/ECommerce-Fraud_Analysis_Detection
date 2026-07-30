import re
import logging
import pandas as pd
import json

from ai.groq_client import get_groq_client, create_chat_completion
from ai.prompt_constants import (
    GROQ_INTENT_MODEL,
    GROQ_REPAIR_MODEL,
    GROQ_SQL_MODEL,
    GROQ_SUMMARY_MODEL,
    MAX_HISTORY,
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
    "phone": "phone",
    "phone_number": "phone",
    "mobile": "phone",
    "mobile_number": "phone",
    "address": "address",
    "default_address": "address",
    "street": "address",
    "ip": "ip",
    "ip_address": "ip",
}

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
                return df.head(MARKDOWN_PREVIEW_ROWS).to_markdown(index=False)
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
    previous_df = sanitize_dataframe_for_llm(previous_df)

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

    data_preview = sanitized_df.head(MARKDOWN_PREVIEW_ROWS).to_markdown(index=False)

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
        logging.warning(_friendly_error_message(e, "recommendations"))
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
    # PII may be queried; UI masking is role-based (Admin full, others masked)
    # via mask_sensitive_dataframe. Copies sent to any LLM are always masked
    # via sanitize_dataframe_for_llm. Only truly forbidden columns are blocked below.

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
        logging.warning("Groq client unavailable. Cannot repair SQL.")
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
        logging.warning(_friendly_error_message(e, "repair"))
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

from utils.pii import can_view_full_pii, mask_address, mask_email, mask_ip, mask_phone


def _mask_email(value):
    if pd.isna(value):
        return value
    return mask_email(str(value))


def _mask_phone(value):
    if pd.isna(value):
        return value
    return mask_phone(str(value))


def _mask_address(value):
    if pd.isna(value):
        return value
    return mask_address(str(value))


def _mask_ip(value):
    if pd.isna(value):
        return value
    return mask_ip(str(value))


def _sensitive_mask_type(column_name):
    key = column_name.lower()
    exact = SENSITIVE_COLUMNS.get(key)
    if exact:
        return exact

    if key == "ip" or "ip_address" in key:
        return "ip"
    if "email" in key:
        return "email"
    if "phone" in key or "mobile" in key:
        return "phone"
    if "address" in key or "street" in key:
        return "address"
    return None


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
    return value


def _apply_pii_masks(df: pd.DataFrame) -> pd.DataFrame:
    """Unconditionally mask known PII columns."""
    masked_df = df.copy()
    for column in masked_df.columns:
        if _sensitive_mask_type(column):
            masked_df[column] = masked_df[column].apply(
                lambda value, col=column: _mask_value(col, value)
            )
    return masked_df


def mask_sensitive_dataframe(
    df: pd.DataFrame,
    analyst: dict | None = None,
) -> pd.DataFrame:
    """Mask PII for UI tables/charts using the same role rules as the analyst portal.

    Admin sees full values; all other roles (and anonymous) see masked values.
    """
    if df is None or df.empty:
        return df
    if can_view_full_pii(analyst):
        return df.copy()
    return _apply_pii_masks(df)


def sanitize_dataframe_for_llm(df: pd.DataFrame) -> pd.DataFrame:
    """Always mask PII before any LLM prompt — never send raw PII to Groq."""
    if df is None or df.empty:
        return df
    return _apply_pii_masks(df)



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
