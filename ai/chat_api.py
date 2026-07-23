"""Headless chat processing for the analyst portal (uses ai/chatbot.py engine)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pandas as pd
from groq import APIConnectionError

from ai.chatbot import (
    ADVISORY_MAX_TOKENS,
    ADVISORY_REASONING_EFFORT,
    ADVISORY_SYSTEM_PROMPT,
    MARKDOWN_PREVIEW_ROWS,
    MAX_HISTORY,
    SQL_MAX_TOKENS,
    SQL_REASONING_EFFORT,
    SQL_SYSTEM_PROMPT,
    STRATEGY_SUMMARY_PROMPT_BASE,
    SUMMARY_MAX_TOKENS,
    SUMMARY_REASONING_EFFORT,
    SUMMARY_SYSTEM_PROMPT_BASE,
    _classify_intent,
    _detect_chart_columns,
    _extract_sql,
    _extract_usage,
    _friendly_error_message,
    _generate_ai_recommendations,
    _get_followup_context,
    _get_last_result_context,
    _repair_sql,
    _restore_dataframe_types,
    _strip_sql_comments,
    _validate_sql,
    _wants_strategy_answer,
    sanitize_dataframe_for_llm,
)
from ai.groq_client import create_chat_completion, get_groq_client
from config import GROQ_API_KEY, GROQ_SQL_MODEL, GROQ_SUMMARY_MODEL
from database.connection import get_pooled_connection, release_pooled_connection
from database.transaction_repository import log_chatbot_interaction


def _empty_response(content: str, status: str = "error", **extra: Any) -> Dict[str, Any]:
    """
    `status` lets the frontend branch cleanly instead of string-matching
    `content`: "error" (something failed), "empty" (valid query, no rows),
    "advisory" (GENERAL answer, no new data), "blocked" (validation failure).
    """
    base = {
        "status": status,
        "content": content,
        "sql": None,
        "rows": None,
        "chart": None,
        "followups": [],
        "business_advice": [],
        "insight_title": "AI Insights",
    }
    base.update(extra)
    return base


def _json_safe(value: Any) -> Any:
    """Coerce a single cell to a JSON-safe native type.

    Handles NaN/NaT (invalid in strict JSON — many frontend JSON.parse
    implementations reject a bare `NaN` token) and numpy scalar types
    (int64/float64), which some serializers choke on.
    """
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float, str, bool)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    # numpy scalar types (int64, float64, bool_) expose .item()
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    return str(value)


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = df.to_dict(orient="records")
    return [{key: _json_safe(value) for key, value in row.items()} for row in records]


def _to_number(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# Chart tabs offered in the portal after each data response.
_PORTAL_CHART_TYPES = ["bar", "hbar", "line", "area", "pie", "table"]


def _build_chart_payload(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Return chart data + selectable types for the portal UI."""
    if df is None or df.empty:
        return None

    work = _restore_dataframe_types(df.copy())
    numeric_cols = work.select_dtypes(include="number").columns.tolist()

    # Single KPI cell → metric card (no multi-chart tabs)
    if len(work) == 1 and len(numeric_cols) == 1 and len(work.columns) <= 2:
        col = numeric_cols[0]
        return {
            "type": "metric",
            "types": ["metric"],
            "label": col.replace("_", " ").title(),
            "value": _to_number(work[col].iloc[0]),
            "x_label": None,
            "y_label": str(col),
            "labels": [col.replace("_", " ").title()],
            "values": [_to_number(work[col].iloc[0])],
        }

    if not numeric_cols or len(work.columns) < 2:
        return None

    x_axis, y_axis = _detect_chart_columns(work)
    if not x_axis or not y_axis:
        return None

    plot = work[[x_axis, y_axis]].dropna()
    if plot.empty:
        return None

    datetime_cols = work.select_dtypes(include=["datetime64"]).columns.tolist()
    category_like = x_axis not in numeric_cols

    if category_like and plot[x_axis].nunique() < len(plot):
        grouped = plot.groupby(x_axis, dropna=False)[y_axis].sum().reset_index()
        plot = grouped

    plot = plot.sort_values(
        y_axis if x_axis not in datetime_cols else x_axis,
        ascending=False if x_axis not in datetime_cols else True,
    ).head(20)

    nunique = int(plot[x_axis].nunique()) if len(plot) else 0
    if x_axis in datetime_cols:
        chart_type = "line"
    elif category_like and nunique <= 5:
        chart_type = "pie"
    else:
        chart_type = "bar"

    labels = [str(v) for v in plot[x_axis].tolist()]
    values = [_to_number(v) for v in plot[y_axis].tolist()]
    if not labels or not values:
        return None

    return {
        "type": chart_type,
        "types": list(_PORTAL_CHART_TYPES),
        "x_label": str(x_axis),
        "y_label": str(y_axis),
        "labels": labels,
        "values": values,
    }


def _generate_insights(
    client,
    user_query: str,
    sanitized_df: pd.DataFrame,
) -> tuple[str, str, int, int]:
    strategy_mode = _wants_strategy_answer(user_query)
    prompt_template = (
        STRATEGY_SUMMARY_PROMPT_BASE if strategy_mode else SUMMARY_SYSTEM_PROMPT_BASE
    )
    insight_title = "Growth Strategies" if strategy_mode else "AI Insights"
    data_preview = sanitized_df.head(MARKDOWN_PREVIEW_ROWS).to_markdown(index=False)
    total_in = total_out = 0

    try:
        completion = create_chat_completion(
            client,
            model=GROQ_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": prompt_template.format(
                        user_query=user_query,
                        data_preview=data_preview,
                    ),
                }
            ],
            temperature=0.3,
            max_tokens=SUMMARY_MAX_TOKENS,
            reasoning_effort=SUMMARY_REASONING_EFFORT,
            include_reasoning=False,
        )
        summary = completion.choices[0].message.content or ""
        in_tok, out_tok = _extract_usage(completion)
        total_in += in_tok
        total_out += out_tok

        finish_reason = getattr(completion.choices[0], "finish_reason", None)
        if finish_reason == "length" or not summary.strip():
            completion = create_chat_completion(
                client,
                model=GROQ_SUMMARY_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": prompt_template.format(
                            user_query=user_query,
                            data_preview=data_preview,
                        ),
                    }
                ],
                temperature=0.3,
                max_tokens=SUMMARY_MAX_TOKENS * 2,
                reasoning_effort=SUMMARY_REASONING_EFFORT,
                include_reasoning=False,
            )
            summary = completion.choices[0].message.content or ""
            in_tok, out_tok = _extract_usage(completion)
            total_in += in_tok
            total_out += out_tok

        if not summary.strip():
            summary = "Unable to generate a written summary. Please review the data below."
    except Exception:
        summary = "Unable to generate a written summary. Please review the data below."

    return summary, insight_title, total_in, total_out


def process_chat_message(user_query: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not user_query:
        return _empty_response("Please enter a question.", status="error")

    if not GROQ_API_KEY:
        return _empty_response(
            "Groq API key is missing. Add GROQ_API_KEY to your .env file.", status="error"
        )

    client = get_groq_client()
    if not client:
        return _empty_response("Unable to initialize Groq client.", status="error")

    recent_messages = history[-MAX_HISTORY:]
    total_input_tokens = 0
    total_output_tokens = 0

    intent, in_tok, out_tok = _classify_intent(client, user_query, recent_messages)
    total_input_tokens += in_tok
    total_output_tokens += out_tok

    if intent == "GENERAL":
        transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent_messages)
        data_context = _get_last_result_context(recent_messages)
        advisory_messages = [
            {
                "role": "system",
                "content": ADVISORY_SYSTEM_PROMPT.format(
                    conversation_context=transcript or "(no prior conversation)",
                    data_context=data_context or "(no prior data table available)",
                    user_query=user_query,
                ),
            }
        ]
        try:
            completion = create_chat_completion(
                client,
                model=GROQ_SUMMARY_MODEL,
                messages=advisory_messages,
                temperature=0.4,
                max_tokens=ADVISORY_MAX_TOKENS,
                reasoning_effort=ADVISORY_REASONING_EFFORT,
                include_reasoning=False,
            )
            answer = completion.choices[0].message.content or ""
            in_tok, out_tok = _extract_usage(completion)
            total_input_tokens += in_tok
            total_output_tokens += out_tok
        except Exception as exc:
            friendly = _friendly_error_message(exc, "summary")
            log_chatbot_interaction(
                user_query,
                None,
                None,
                f"ADVISORY_ERROR: {exc}",
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )
            return _empty_response(friendly, status="error")

        log_chatbot_interaction(
            user_query,
            None,
            None,
            answer,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        return _empty_response(
            answer.strip() or "No answer generated.",
            status="advisory",
            insight_title="AI Insights",
        )

    llm_payload = [{"role": "system", "content": SQL_SYSTEM_PROMPT}]
    if intent == "FOLLOWUP_QUERY":
        followup_context = _get_followup_context(recent_messages)
        if followup_context:
            llm_payload.append(
                {
                    "role": "user",
                    "content": (
                        "This is a follow-up question. Use the context below and respond with ONLY SQL.\n\n"
                        f"{followup_context}"
                    ),
                }
            )
    llm_payload.append({"role": "user", "content": user_query})

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
    except APIConnectionError as exc:
        friendly = _friendly_error_message(exc, "connection")
        log_chatbot_interaction(
            user_query,
            None,
            None,
            f"CONNECTION_ERROR: {exc}",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        return _empty_response(friendly, status="error")
    except Exception as exc:
        friendly = _friendly_error_message(exc, "generation")
        log_chatbot_interaction(
            user_query,
            None,
            None,
            f"GENERATION_ERROR: {exc}",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        return _empty_response(friendly, status="error")

    is_valid, validation_error = _validate_sql(sql_query)
    if is_valid:
        sql_query = _strip_sql_comments(sql_query)
    else:
        repaired, repair_in_tok, repair_out_tok = _repair_sql(sql_query, validation_error)
        total_input_tokens += repair_in_tok
        total_output_tokens += repair_out_tok
        repaired_valid, _ = _validate_sql(repaired)
        if repaired_valid:
            sql_query = _strip_sql_comments(repaired)
        else:
            log_chatbot_interaction(
                user_query,
                sql_query,
                None,
                f"BLOCKED: {validation_error}",
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )
            # Do not expose SQL to the UI.
            return _empty_response(validation_error, status="blocked")

    conn = None
    try:
        conn = get_pooled_connection()
        result_df = pd.read_sql_query(sql_query, conn)
    except Exception as exc:
        friendly = _friendly_error_message(exc, "execution")
        log_chatbot_interaction(
            user_query,
            sql_query,
            None,
            f"DB_ERROR: {exc}",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        return _empty_response(friendly, status="error", sql=sql_query)
    finally:
        if conn:
            release_pooled_connection(conn)

    if result_df.empty:
        msg = "No matching data found for your question. Try rephrasing it."
        log_chatbot_interaction(
            user_query,
            sql_query,
            None,
            "The query executed successfully but returned no matching rows.",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        return _empty_response(msg, status="empty", sql=sql_query, rows=[])

    # Everything from here on touches pandas/chart/LLM logic that can throw
    # in ways not anticipated above (bad dtypes, groupby edge cases, etc.).
    # A raw exception here shouldn't surface as an unhandled 500 to the
    # frontend — wrap it so the person always gets a usable response.
    try:
        result_df = _restore_dataframe_types(result_df)
        sanitized_df = sanitize_dataframe_for_llm(result_df)

        summary, insight_title, sum_in, sum_out = _generate_insights(
            client, user_query, sanitized_df
        )
        total_input_tokens += sum_in
        total_output_tokens += sum_out

        conversation_history = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in recent_messages
        )
        recommendations = _generate_ai_recommendations(
            client=client,
            user_query=user_query,
            sql_query=sql_query,
            sanitized_df=sanitized_df,
            executive_summary=summary,
            conversation_history=conversation_history,
        )

        rows = _df_to_records(sanitized_df.head(10))
        chart = _build_chart_payload(sanitized_df.head(100))
    except Exception as exc:
        friendly = _friendly_error_message(exc, "summary")
        log_chatbot_interaction(
            user_query,
            sql_query,
            result_df,
            f"POSTPROCESS_ERROR: {exc}",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
        # Query succeeded — return masked rows so PII is never shown raw.
        try:
            safe_rows = _df_to_records(sanitize_dataframe_for_llm(result_df).head(10))
        except Exception:
            safe_rows = []
        return _empty_response(
            friendly,
            status="error",
            sql=sql_query,
            rows=safe_rows,
        )

    log_chatbot_interaction(
        user_query,
        sql_query,
        sanitized_df,
        summary,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
    )

    return {
        "status": "success",
        "content": summary,
        # sql is returned only so the client can pass it back for follow-ups;
        # the portal UI must not display it.
        "sql": sql_query,
        "rows": rows,
        "chart": chart,
        "followups": recommendations.get("followups", [])[:5],
        "business_advice": recommendations.get("business_advice", [])[:5],
        "insight_title": insight_title,
    }