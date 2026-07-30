"""Lightweight session tokens for the React analyst portal."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from fastapi import Cookie, Depends, Header, HTTPException

from auth.analyst_auth import (
    ALL_PAGES,
    ANALYST_FIELDS,
    authenticate_analyst,
    get_granted_pages,
    is_admin,
)
from config import DB_CONFIG, PORTAL_SECRET, PORTAL_TOKEN_TTL
import psycopg2

TOKEN_TTL_SECONDS = PORTAL_TOKEN_TTL
PORTAL_SESSION_COOKIE = "metro_cart_session"


def _ordered_pages(granted) -> list[str]:
    """Return granted pages in sidebar order (chatbot last)."""
    granted_set = set(granted)
    return [page for page in ALL_PAGES if page in granted_set]


def _sign(payload: str) -> str:
    return hmac.new(PORTAL_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(analyst_id: str) -> str:
    body = json.dumps({"sub": analyst_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS})
    token = f"{body}.{_sign(body)}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def verify_session_token(token: str) -> Optional[str]:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        body, signature = decoded.rsplit(".", 1)
        if not hmac.compare_digest(_sign(body), signature):
            return None
        payload = json.loads(body)
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("sub")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def authenticate_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            analyst = authenticate_analyst(cur, username, password, conn=conn)
            if not analyst:
                return None
            return _session_for_analyst(cur, analyst)


def _session_for_analyst(cur, analyst: Dict[str, Any]) -> Dict[str, Any]:
    granted = get_granted_pages(cur, analyst)
    return {
        "analyst": analyst,
        "granted_pages": _ordered_pages(granted),
        "is_admin": is_admin(analyst),
        "token": create_session_token(analyst["analyst_id"]),
    }


def get_analyst_by_id(analyst_id: str) -> Optional[Dict[str, Any]]:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT analyst_id, employee_name, username, role
                FROM master.analyst_users
                WHERE analyst_id = %s
                """,
                (analyst_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            analyst = dict(zip(ANALYST_FIELDS, row))
            granted = get_granted_pages(cur, analyst)
    return {
        "analyst": analyst,
        "granted_pages": _ordered_pages(granted),
        "is_admin": is_admin(analyst),
    }


def get_session_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Build an analyst session from username (used after Keycloak SSO)."""
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT analyst_id, employee_name, username, role
                FROM master.analyst_users
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return None
            analyst = dict(zip(ANALYST_FIELDS, row))
            return _session_for_analyst(cur, analyst)


def _extract_session_token(
    authorization: Optional[str],
    portal_session: Optional[str],
) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    if portal_session:
        return portal_session.strip()
    return None


def get_current_session(
    authorization: Optional[str] = Header(None),
    portal_session: Optional[str] = Cookie(None, alias=PORTAL_SESSION_COOKIE),
) -> Dict[str, Any]:
    token = _extract_session_token(authorization, portal_session)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    analyst_id = verify_session_token(token)
    if not analyst_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if str(analyst_id).startswith("customer:"):
        raise HTTPException(status_code=401, detail="Analyst session required")
    session = get_analyst_by_id(analyst_id)
    if not session:
        raise HTTPException(status_code=401, detail="User not found")
    return session


def require_page(page_key: str):
    def _checker(session: Dict[str, Any] = Depends(get_current_session)) -> Dict[str, Any]:
        if page_key not in session["granted_pages"]:
            raise HTTPException(status_code=403, detail="Access denied for this page")
        return session

    return _checker


def require_admin(session: Dict[str, Any] = Depends(get_current_session)) -> Dict[str, Any]:
    """Require an authenticated Admin analyst (stricter than page RBAC)."""
    if not session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    return session
