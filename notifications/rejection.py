"""Customer notification when an order is rejected."""

from __future__ import annotations

import html
import logging
from typing import Any, Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection

from config import DB_CONFIG, EMAIL_ALERTS_ENABLED, is_graph_mail_configured
from notifications.graph_client import send_mail_safe

logger = logging.getLogger(__name__)


def _fetch_order_for_rejection_email(cursor: Any, order_id: str) -> Optional[dict]:
    cursor.execute(
        """
        SELECT
            order_id,
            user_id,
            customer_name,
            email,
            product_name,
            amount,
            order_status
        FROM master.orders
        WHERE order_id = %s
        """,
        (order_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    cols = [d.name for d in cursor.description]
    return dict(zip(cols, row))


def build_rejection_bodies(order: dict) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body) — generic content, no fraud details."""
    order_id = str(order.get("order_id") or "")
    customer = str(order.get("customer_name") or "Customer")
    product = str(order.get("product_name") or "your item")
    amount = order.get("amount", "")

    subject = f"Order Update - {order_id} could not be processed"
    text = (
        f"Hello {customer},\n\n"
        f"We are writing to let you know that your order {order_id} "
        f"({product}, amount {amount}) could not be processed at this time.\n\n"
        "If you have questions, please contact support with your order reference.\n\n"
        "Thank you,\nMetro Cart"
    )
    html_body = (
        f"<p>Hello {html.escape(customer)},</p>"
        f"<p>We are writing to let you know that your order "
        f"<b>{html.escape(order_id)}</b> "
        f"({html.escape(product)}, amount {html.escape(str(amount))}) "
        f"could not be processed at this time.</p>"
        "<p>If you have questions, please contact support with your order reference.</p>"
        "<p>Thank you,<br/>Metro Cart</p>"
    )
    return subject, text, html_body


def notify_order_rejected(
    order_id: str,
    conn: PgConnection | None = None,
    *,
    force: bool = False,
) -> dict:
    """
    Send a generic rejection email to the order's customer email.
    Safe to call after DB commit; never raises to callers when force is false path via safe send.
    """
    if not force and not EMAIL_ALERTS_ENABLED:
        logger.info("Rejection email skipped (EMAIL_ALERTS_ENABLED=false) order=%s", order_id)
        return {"skipped": True, "reason": "disabled", "order_id": order_id}

    if not is_graph_mail_configured():
        logger.warning("Rejection email skipped (Graph not configured) order=%s", order_id)
        return {"skipped": True, "reason": "not_configured", "order_id": order_id}

    own_conn = conn is None
    if own_conn:
        conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            order = _fetch_order_for_rejection_email(cur, order_id)

        if not order:
            return {"skipped": True, "reason": "order_not_found", "order_id": order_id}

        to_email = (order.get("email") or "").strip()
        if not to_email:
            logger.warning("Rejection email skipped (no email on order) order=%s", order_id)
            return {"skipped": True, "reason": "no_email", "order_id": order_id}

        subject, text_body, html_body = build_rejection_bodies(order)
        ok = send_mail_safe(
            to_emails=[to_email],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        result = {
            "skipped": False,
            "sent": ok,
            "order_id": order_id,
            "to": to_email,
            "subject": subject,
        }
        if ok:
            logger.info("Rejection email sent order=%s to=%s", order_id, to_email)
        return result
    finally:
        if own_conn and conn is not None:
            conn.close()


def notify_orders_rejected(order_ids: list[str]) -> None:
    """Best-effort notify for many orders (batch reject)."""
    for order_id in order_ids:
        try:
            notify_order_rejected(order_id)
        except Exception:
            logger.exception("Rejection notify failed for order=%s", order_id)
