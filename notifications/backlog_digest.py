"""Backlog order digest emails for analyst roles (Admin by default)."""

from __future__ import annotations

import html
import logging
from typing import Any, List, Sequence

import psycopg2
from psycopg2.extensions import connection as PgConnection

from config import (
    BACKLOG_ALERT_ROLES,
    DB_CONFIG,
    EMAIL_ALERTS_ENABLED,
    is_graph_mail_configured,
)
from fraud_engine.backlog import detect_backlog_orders, get_backlog_stats
from notifications.graph_client import send_mail_safe

logger = logging.getLogger(__name__)

_MAX_ROWS_IN_EMAIL = 25


def fetch_backlog_alert_recipients(
    cursor: Any,
    roles: Sequence[str] = BACKLOG_ALERT_ROLES,
) -> List[str]:
    """Distinct non-empty emails for the given analyst roles."""
    if not roles:
        return []
    cursor.execute(
        """
        SELECT DISTINCT LOWER(TRIM(email)) AS email
        FROM master.analyst_users
        WHERE role = ANY(%s)
          AND email IS NOT NULL
          AND TRIM(email) <> ''
        ORDER BY 1
        """,
        (list(roles),),
    )
    return [row[0] for row in cursor.fetchall()]


def _format_minutes(value: Any) -> str:
    try:
        return f"{float(value):.0f}"
    except (TypeError, ValueError):
        return "-"


def build_backlog_digest_bodies(backlog_df, stats: dict) -> tuple[str, str]:
    """Return (text_body, html_body) for the backlog digest."""
    total = int(stats.get("total_backlog") or 0)
    max_overdue = _format_minutes(stats.get("max_minutes_overdue"))
    oldest_id = stats.get("oldest_order_id") or "-"

    text_lines = [
        "Fraud Portal - Backlog Orders Alert",
        "",
        f"Total backlog orders: {total}",
        f"Oldest order ID: {oldest_id}",
        f"Max minutes overdue: {max_overdue}",
        "",
    ]

    html_parts = [
        "<h2>Fraud Portal - Backlog Orders Alert</h2>",
        f"<p><b>Total backlog orders:</b> {total}<br/>",
        f"<b>Oldest order ID:</b> {html.escape(str(oldest_id))}<br/>",
        f"<b>Max minutes overdue:</b> {html.escape(max_overdue)}</p>",
    ]

    if total == 0 or backlog_df is None or backlog_df.empty:
        text_lines.append("No overdue review-queue orders right now.")
        html_parts.append("<p>No overdue review-queue orders right now.</p>")
        return "\n".join(text_lines), "\n".join(html_parts)

    text_lines.append("Orders:")
    html_parts.append(
        "<table border='1' cellpadding='6' cellspacing='0' "
        "style='border-collapse:collapse;font-family:sans-serif;font-size:13px'>"
        "<thead><tr>"
        "<th>Order ID</th><th>Customer</th><th>Product</th>"
        "<th>Amount</th><th>Status</th><th>Minutes overdue</th><th>Rules</th>"
        "</tr></thead><tbody>"
    )

    rows = backlog_df.head(_MAX_ROWS_IN_EMAIL)
    for _, row in rows.iterrows():
        order_id = str(row.get("order_id", ""))
        customer = str(row.get("customer_name", "") or "")
        product = str(row.get("product_name", "") or "")
        amount = row.get("amount", "")
        status = str(row.get("order_status", "") or "")
        overdue = _format_minutes(row.get("minutes_overdue"))
        rules = str(row.get("rule_name", "") or "")
        text_lines.append(
            f"- {order_id} | {customer} | {product} | {amount} | "
            f"{status} | overdue {overdue}m | {rules}"
        )
        html_parts.append(
            "<tr>"
            f"<td>{html.escape(order_id)}</td>"
            f"<td>{html.escape(customer)}</td>"
            f"<td>{html.escape(product)}</td>"
            f"<td>{html.escape(str(amount))}</td>"
            f"<td>{html.escape(status)}</td>"
            f"<td>{html.escape(overdue)}</td>"
            f"<td>{html.escape(rules)}</td>"
            "</tr>"
        )

    html_parts.append("</tbody></table>")
    if total > _MAX_ROWS_IN_EMAIL:
        note = f"Showing first {_MAX_ROWS_IN_EMAIL} of {total} backlog orders."
        text_lines.append("")
        text_lines.append(note)
        html_parts.append(f"<p><i>{html.escape(note)}</i></p>")

    return "\n".join(text_lines), "\n".join(html_parts)


def send_backlog_digest(
    conn: PgConnection | None = None,
    *,
    force: bool = False,
) -> dict:
    """
    Detect backlog orders and email configured analyst roles.

    Returns a small status dict for logging / CLI.
    When EMAIL_ALERTS_ENABLED is false (and force is false), this is a no-op.
    """
    if not force and not EMAIL_ALERTS_ENABLED:
        logger.info("Backlog digest skipped (EMAIL_ALERTS_ENABLED=false).")
        return {"skipped": True, "reason": "disabled"}

    if not is_graph_mail_configured():
        logger.warning("Backlog digest skipped (Graph mail not configured).")
        return {"skipped": True, "reason": "not_configured"}

    own_conn = conn is None
    if own_conn:
        conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            recipients = fetch_backlog_alert_recipients(cur)
            backlog_df = detect_backlog_orders(cur)
            stats = get_backlog_stats(cur)

        if not recipients:
            logger.warning(
                "Backlog digest skipped (no emails for roles %s).",
                BACKLOG_ALERT_ROLES,
            )
            return {
                "skipped": True,
                "reason": "no_recipients",
                "total_backlog": int(stats.get("total_backlog") or 0),
            }

        total = int(stats.get("total_backlog") or 0)
        subject = f"[Fraud Portal] Backlog Alert - {total} order(s) overdue"
        text_body, html_body = build_backlog_digest_bodies(backlog_df, stats)
        ok = send_mail_safe(
            to_emails=recipients,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        result = {
            "skipped": False,
            "sent": ok,
            "recipients": recipients,
            "total_backlog": total,
            "subject": subject,
        }
        if ok:
            logger.info(
                "Backlog digest sent to %s (total_backlog=%s).",
                recipients,
                total,
            )
        return result
    finally:
        if own_conn and conn is not None:
            conn.close()
