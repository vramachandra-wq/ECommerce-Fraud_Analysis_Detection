"""Keycloak OIDC helpers for analyst portal SSO (optional; local login unchanged)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from config import (
    API_BASE_URL,
    CORS_ALLOW_ORIGINS,
    KEYCLOAK_ADMIN,
    KEYCLOAK_ADMIN_PASSWORD,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_ENABLED,
    KEYCLOAK_REALM,
    KEYCLOAK_REDIRECT_URI,
    KEYCLOAK_URL,
    PORTAL_SECRET,
    SSO_DEFAULT_RETURN_TO,
)

_STATE_TTL_SECONDS = 600


def sso_is_configured() -> bool:
    return bool(
        KEYCLOAK_ENABLED
        and KEYCLOAK_URL
        and KEYCLOAK_REALM
        and KEYCLOAK_CLIENT_ID
        and KEYCLOAK_CLIENT_SECRET
        and KEYCLOAK_REDIRECT_URI
    )


def realm_base_url() -> str:
    return f"{KEYCLOAK_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}"


def authorization_endpoint() -> str:
    return f"{realm_base_url()}/protocol/openid-connect/auth"


def token_endpoint() -> str:
    return f"{realm_base_url()}/protocol/openid-connect/token"


def userinfo_endpoint() -> str:
    return f"{realm_base_url()}/protocol/openid-connect/userinfo"


def admin_base_url() -> str:
    return f"{KEYCLOAK_URL.rstrip('/')}/admin/realms/{KEYCLOAK_REALM}"


def _sign(payload: str) -> str:
    return hmac.new(PORTAL_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_pkce_pair() -> Tuple[str, str]:
    """Return (code_verifier, code_challenge) for S256 PKCE."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def create_oauth_state(return_to: str, *, code_verifier: str) -> str:
    body = json.dumps(
        {
            "return_to": return_to,
            "code_verifier": code_verifier,
            "nonce": secrets.token_urlsafe(16),
            "exp": int(time.time()) + _STATE_TTL_SECONDS,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    token = f"{body}.{_sign(body)}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def parse_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    try:
        decoded = base64.urlsafe_b64decode(state.encode()).decode()
        body, signature = decoded.rsplit(".", 1)
        if not hmac.compare_digest(_sign(body), signature):
            return None
        payload = json.loads(body)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _allowed_return_origins() -> set[str]:
    origins: set[str] = set()
    for raw in (API_BASE_URL, SSO_DEFAULT_RETURN_TO, *CORS_ALLOW_ORIGINS):
        if not raw or raw == "*":
            continue
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")
    # Always allow the API host itself (static portal).
    api = urlparse(API_BASE_URL)
    if api.scheme and api.netloc:
        origins.add(f"{api.scheme}://{api.netloc}")
    return origins


def normalize_return_to(candidate: Optional[str]) -> str:
    default = SSO_DEFAULT_RETURN_TO or f"{API_BASE_URL.rstrip('/')}/portal/"
    if not candidate:
        return default
    candidate = candidate.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return default
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _allowed_return_origins():
        return default
    # Keep path/query; strip fragment.
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{origin}{path}{query}"


def build_authorize_url(*, state: str, code_challenge: str) -> str:
    params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": KEYCLOAK_REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{authorization_endpoint()}?{urlencode(params)}"


def exchange_code_for_tokens(code: str, *, code_verifier: str) -> Dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            token_endpoint(),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": KEYCLOAK_REDIRECT_URI,
                "client_id": KEYCLOAK_CLIENT_ID,
                "client_secret": KEYCLOAK_CLIENT_SECRET,
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        return response.json()


def fetch_userinfo(access_token: str) -> Dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            userinfo_endpoint(),
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def username_from_userinfo(userinfo: Dict[str, Any]) -> Optional[str]:
    for key in ("preferred_username", "username", "email"):
        value = userinfo.get(key)
        if isinstance(value, str) and value.strip():
            # Map email local-part only when it is the preferred claim fallback.
            if key == "email" and "@" in value:
                return value.split("@", 1)[0].strip()
            return value.strip()
    return None


def logout_endpoint() -> str:
    return f"{realm_base_url()}/protocol/openid-connect/logout"


def _admin_access_token() -> str:
    if not KEYCLOAK_ADMIN or not KEYCLOAK_ADMIN_PASSWORD:
        raise RuntimeError("SSO admin credentials are not configured.")
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{KEYCLOAK_URL.rstrip('/')}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
        )
        response.raise_for_status()
        body = response.json()
    token = str(body.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("SSO admin token response missing access_token.")
    return token


def sync_keycloak_password(username: str, new_password: str) -> tuple[bool, Optional[str]]:
    """
    Best-effort sync of a local analyst password into Keycloak.

    Returns (True, None) when synced or not applicable, else (False, reason).
    """
    if not sso_is_configured():
        return True, None
    # Admin API is optional for OIDC login; without it, skip sync rather than
    # blocking local password changes that still apply to Postgres auth.
    if not KEYCLOAK_ADMIN or not KEYCLOAK_ADMIN_PASSWORD:
        return True, None
    username = (username or "").strip()
    if not username:
        return False, "missing_username"
    try:
        admin_token = _admin_access_token()
        with httpx.Client(timeout=20.0) as client:
            users = client.get(
                f"{admin_base_url()}/users",
                params={"username": username, "exact": "true"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            users.raise_for_status()
            matches = users.json()
            if not matches:
                return True, None
            user_id = str(matches[0].get("id") or "").strip()
            if not user_id:
                return False, "keycloak_user_id_missing"
            reset = client.put(
                f"{admin_base_url()}/users/{user_id}/reset-password",
                json={"type": "password", "temporary": False, "value": new_password},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            reset.raise_for_status()
            return True, None
    except (httpx.HTTPError, RuntimeError) as exc:
        return False, str(exc)


def build_logout_url(
    *,
    post_logout_redirect_uri: str,
    id_token_hint: Optional[str] = None,
) -> str:
    params: Dict[str, str] = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": post_logout_redirect_uri,
    }
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    return f"{logout_endpoint()}?{urlencode(params)}"


def complete_sso_login(
    code: str, *, code_verifier: str
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Exchange the auth code and return (username, id_token, error_message).
    Caller maps username to a local analyst session and stores id_token for logout.
    """
    if not code_verifier:
        return None, None, "Missing PKCE code_verifier"
    try:
        tokens = exchange_code_for_tokens(code, code_verifier=code_verifier)
    except httpx.HTTPError as exc:
        return None, None, f"Token exchange failed: {exc}"

    access_token = tokens.get("access_token")
    if not access_token:
        return None, None, "Token response missing access_token"

    id_token = tokens.get("id_token")
    if isinstance(id_token, str):
        id_token = id_token.strip() or None
    else:
        id_token = None

    try:
        userinfo = fetch_userinfo(access_token)
    except httpx.HTTPError as exc:
        return None, None, f"UserInfo request failed: {exc}"

    username = username_from_userinfo(userinfo)
    if not username:
        return None, None, "SSO userinfo missing preferred_username"
    return username, id_token, None


def append_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = value
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            parsed.params,
            urlencode(query),
            "",
        )
    )
