import os
import re
import pandas as pd
import streamlit as st

from groq import APIConnectionError
from ai.groq_client import get_groq_client, create_chat_completion
from ai.prompt_constants import (
    GROQ_API_KEY,
    GROQ_REPAIR_MODEL,
    GROQ_SQL_MODEL,
    GROQ_SUMMARY_MODEL,
    MAX_HISTORY,
    MAX_STORED_MESSAGES,
    MARKDOWN_PREVIEW_ROWS,
    SCHEMA_CONTEXT,
    SQL_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT_BASE,
    REPAIR_PROMPT_TEMPLATE,
    INTENT_SYSTEM_PROMPT,
    SUMMARY_MAX_TOKENS,
    INTENT_MAX_TOKENS,
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
    "customers.password",
    "password",
}


def _extract_sql(text: str) -> str:
    """Extract SQL from markdown code block with improved regex."""
    match = re.search(
        r"```\s*sql\s*\n(.*?)\n\s*```",
        text,
        re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else text.strip()


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
    """Classify whether user_query is a NEW question or a FOLLOWUP to history.

    Returns (label, input_tokens, output_tokens). Label defaults to "NEW"
    (the safer, more isolated choice — a false "NEW" just means a follow-up
    loses some context; a false "FOLLOWUP" can drag irrelevant prior context
    into an unrelated query and corrupt SQL generation) on any classification
    failure or ambiguous output.
    """
    if not history:
        return "NEW", 0, 0

    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )

    try:
        completion = create_chat_completion(
            client,
            model=GROQ_SQL_MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Conversation history:\n{transcript}\n\nLatest question:\n{user_query}",
                },
            ],
            temperature=0.0,
            max_tokens=INTENT_MAX_TOKENS,
        )
        label = completion.choices[0].message.content.strip().upper()
        in_tok, out_tok = _extract_usage(completion)
        return ("FOLLOWUP" if "FOLLOWUP" in label else "NEW"), in_tok, out_tok
    except Exception:
        # If classification fails for any reason, fall back to treating the
        # query as standalone rather than blocking the pipeline on it.
        return "NEW", 0, 0


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL query with comprehensive checks."""
    sql = _strip_sql_comments(sql)
    sql_lower = sql.lower().strip()

    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        return False, "Only SELECT queries are permitted."

    for kw in _BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", sql_lower):
            return False, f"Blocked keyword detected: `{kw.upper()}`."

    for col in SENSITIVE_COLUMNS:
        if col in sql_lower:
            return False, f"Access to sensitive column '{col}' is prohibited."

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
            max_tokens=700,
        )
        in_tok, out_tok = _extract_usage(response)
        return _extract_sql(response.choices[0].message.content), in_tok, out_tok
    except Exception as e:
        st.warning(f"⚠️ SQL repair failed: {str(e)}")
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
    if df.empty or len(df.columns) < 2:
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    object_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    if not numeric_cols:
        return

    y_axis = _get_best_axis(df, numeric_cols, ['count', 'amount', 'total', 'value']) or numeric_cols[0]

    if datetime_cols:
        x_axis = _get_best_axis(df, datetime_cols, ['timestamp', 'date', 'created']) or datetime_cols[0]

        st.markdown("### 📈 Trend Analysis")
        try:
            chart_df = (
                df[[x_axis, y_axis]]
                .sort_values(x_axis)
                .set_index(x_axis)
            )
            st.line_chart(chart_df, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render line chart: {str(e)}")
        return

    if object_cols:
        x_axis = _get_best_axis(df, object_cols, ['status', 'category', 'type', 'name']) or object_cols[0]
        unique_values = df[x_axis].nunique()

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

        if len(df) >= 6:
            st.markdown("### 📊 Comparison")
            try:
                chart_df = (
                    df[[x_axis, y_axis]]
                    .sort_values(y_axis)
                    .set_index(x_axis)
                )
                st.bar_chart(chart_df, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render bar chart: {str(e)}")
            return

        st.markdown("### 📊 Comparison")
        try:
            chart_df = df[[x_axis, y_axis]].set_index(x_axis)
            st.bar_chart(chart_df, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render bar chart: {str(e)}")
        return

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


def _run_query_pipeline(user_query: str) -> None:
    client = get_groq_client()
    if not client:
        # UPDATED: Directs users to check the .env file configuration
        st.error("🔑 Groq API key missing — add `GROQ_API_KEY` to your `.env` file.")
        return

    recent_messages = st.session_state.messages[-MAX_HISTORY:]
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

                llm_payload = [
                    {
                        "role": "system",
                        "content": SQL_SYSTEM_PROMPT,
                    }
                ]

                if intent == "FOLLOWUP":
                    status.write("↪️ Detected follow-up question — using prior context")
                    for msg in recent_messages:
                        llm_payload.append({
                            "role": msg["role"],
                            "content": msg["content"],
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
                        max_tokens=600,
                    )
                    sql_query = _extract_sql(completion.choices[0].message.content)
                    in_tok, out_tok = _extract_usage(completion)
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok
                except APIConnectionError as e:
                    import traceback
                    st.error("🔌 Unable to connect to Groq. Check network access to https://api.groq.com and your firewall/proxy settings.")
                    st.exception(e)
                    st.code(traceback.format_exc())
                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        f"CONNECTION_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    return
                except Exception as e:
                    import traceback
                    st.exception(e)
                    st.code(traceback.format_exc())
                    log_chatbot_interaction(
                        user_query,
                        None,
                        None,
                        f"GENERATION_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    return

                is_valid, validation_error = _validate_sql(sql_query)
                if is_valid:
                    sql_query = _strip_sql_comments(sql_query)
                if not is_valid:
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
                        with st.expander("🛠️ View Generated Query", expanded=False):
                            st.code(sql_query, language="sql")
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
                    status.update(label="❌ Database execution failed", state="complete", expanded=False)
                    st.error(f"Database Error: {str(e)}")
                    log_chatbot_interaction(
                        user_query,
                        sql_query,
                        None,
                        f"DB_ERROR: {str(e)}",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    return
                finally:
                    if conn:
                        release_pooled_connection(conn)

                if result_df.empty:
                    status.update(label="⚠️ Query returned zero rows", state="complete", expanded=False)
                    msg = "The query executed successfully but returned no matching rows."
                    st.info(msg)
                    with st.expander("🛠️ View Compiled Execution Query", expanded=False):
                        st.code(sql_query, language="sql")
                    log_chatbot_interaction(
                        user_query,
                        sql_query,
                        None,
                        msg,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": msg, "sql": sql_query, "df": None}
                    )
                    return

                result_df = _restore_dataframe_types(result_df)
                status.write("📝 Generating executive insight summary…")
                data_preview = result_df.head(MARKDOWN_PREVIEW_ROWS).to_markdown(index=False)

                try:
                    summary_completion = create_chat_completion(
                        client,
                        model=GROQ_SUMMARY_MODEL,
                        messages=[{
                            "role": "system",
                            "content": SUMMARY_SYSTEM_PROMPT_BASE.format(
                                user_query=user_query,
                                data_preview=data_preview,
                            ),
                        }],
                        temperature=0.3,
                        max_tokens=SUMMARY_MAX_TOKENS,
                    )
                    assistant_summary = summary_completion.choices[0].message.content
                    in_tok, out_tok = _extract_usage(summary_completion)
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok
                    finish_reason = getattr(
                        summary_completion.choices[0], "finish_reason", None
                    )
                    if finish_reason == "length":
                        # Ran out of tokens mid-summary — retry once with a
                        # larger budget rather than showing a cut-off answer.
                        summary_completion = create_chat_completion(
                            client,
                            model=GROQ_SUMMARY_MODEL,
                            messages=[{
                                "role": "system",
                                "content": SUMMARY_SYSTEM_PROMPT_BASE.format(
                                    user_query=user_query,
                                    data_preview=data_preview,
                                ),
                            }],
                            temperature=0.3,
                            max_tokens=SUMMARY_MAX_TOKENS * 2,
                        )
                        assistant_summary = summary_completion.choices[0].message.content
                        in_tok, out_tok = _extract_usage(summary_completion)
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok
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
                    "df": result_df.to_dict(orient="records"),
                })

                if len(st.session_state.messages) > MAX_STORED_MESSAGES:
                    st.session_state.messages = st.session_state.messages[-MAX_STORED_MESSAGES:]

            except Exception as e:
                status.update(label="❌ Pipeline error", state="complete", expanded=False)
                err_msg = f"An unexpected error occurred: {str(e)}"
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
        # st.markdown("---")
        # st.markdown("### ⚙️ Analytics Engine")
        # st.caption("**Domain:** E-commerce Fraud Detection")
        # st.caption("**Database:** PostgreSQL")
        # st.caption("**Schema:** master")
        # st.caption("**LLM Provider:** Groq")
        # st.caption(f"**SQL Model:** `{GROQ_SQL_MODEL}`")
        # st.caption(f"**Repair Model:** `{GROQ_REPAIR_MODEL}`")
        # st.caption(f"**Summary Model:** `{GROQ_SUMMARY_MODEL}`")
        st.markdown("---")
        st.markdown("### 🔌 Connection Status")
        if GROQ_API_KEY:
            st.success("✅ Groq Connected")
        else:
            st.error("❌ Groq API Key Missing")
        # st.markdown("---")
        # st.markdown(f"### 📊 Session Info")
        # st.caption(f"Messages in history: {len(st.session_state.messages)}")
        # st.markdown("---")
        if st.button(
            "🗑️ Clear Chat History",
            use_container_width=True,
            key="clear_chat_btn",
        ):
            st.session_state.messages = []
            st.rerun()

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