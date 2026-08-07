"""Microsoft Graph mail client (application permission Mail.Send)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, Optional, Sequence

from config import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    GRAPH_SENDER_EMAIL,
    GRAPH_SENDER_NAME,
)

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

_cached_token: Optional[str] = None
_cached_expires_at: float = 0.0


def get_graph_access_token(*, force_refresh: bool = False) -> str:
    """Client-credentials token for Graph. Cached until near expiry."""
    global _cached_token, _cached_expires_at
    now = time.time()
    if (
        not force_refresh
        and _cached_token
        and now < (_cached_expires_at - 60)
    ):
        return _cached_token

    if not (AZURE_CLIENT_ID and AZURE_TENANT_ID and AZURE_CLIENT_SECRET):
        raise RuntimeError(
            "Graph mail is not configured. Set Application_ID / Tenent_ID / Secret_Value "
            "(or AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET)."
        )

    form = urllib.parse.urlencode(
        {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _TOKEN_URL.format(tenant=AZURE_TENANT_ID),
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())

    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in Graph token response: {payload}")

    _cached_token = token
    _cached_expires_at = now + float(payload.get("expires_in", 3600))
    return token


def send_mail(
    *,
    to_emails: Sequence[str],
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
    save_to_sent_items: bool = True,
) -> None:
    """
    Send one email via Graph /users/{sender}/sendMail.

    to_emails are de-duplicated (case-insensitive). Raises on HTTP failure.
    """
    recipients = sorted(
        {email.strip() for email in to_emails if email and email.strip()},
        key=str.lower,
    )
    if not recipients:
        raise ValueError("No recipient emails provided")

    sender = (sender_email or GRAPH_SENDER_EMAIL).strip()
    if not sender:
        raise ValueError("GRAPH_SENDER_EMAIL is not configured")

    token = get_graph_access_token()
    message = {
        "subject": subject,
        "body": {
            "contentType": "HTML" if html_body else "Text",
            "content": html_body if html_body else text_body,
        },
        "toRecipients": [
            {"emailAddress": {"address": addr}} for addr in recipients
        ],
    }
    # Optional display name is not a separate Graph field on sendMail From;
    # mailbox identity comes from the user path. Keep name for logging only.
    _ = sender_name or GRAPH_SENDER_NAME

    payload = {
        "message": message,
        "saveToSentItems": "true" if save_to_sent_items else "false",
    }
    url = _SEND_URL.format(sender=urllib.parse.quote(sender))
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # 202 Accepted with empty body is normal.
            logger.info(
                "Graph sendMail accepted (HTTP %s) to %s subject=%r",
                resp.status,
                recipients,
                subject,
            )
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        logger.error("Graph sendMail failed HTTP %s: %s", e.code, detail)
        raise RuntimeError(f"Graph sendMail failed HTTP {e.code}: {detail}") from e


def send_mail_safe(
    *,
    to_emails: Iterable[str],
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send mail; log and return False on failure (never raise)."""
    try:
        send_mail(
            to_emails=list(to_emails),
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return True
    except Exception:
        logger.exception("Failed to send email subject=%r", subject)
        return False
