"""Cookie helpers for portal auth sessions (Secure flag env-aware)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from starlette.responses import Response

from config import COOKIE_SECURE


def portal_cookie_kwargs(*, max_age: Optional[int] = None) -> Dict[str, Any]:
    """Shared attributes for portal session / SSO cookies."""
    kwargs: Dict[str, Any] = {
        "httponly": True,
        "samesite": "lax",
        "path": "/",
        "secure": COOKIE_SECURE,
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    return kwargs


def clear_portal_cookie(response: Response, key: str) -> None:
    """Delete a cookie with the same attributes used when it was set."""
    response.delete_cookie(
        key,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
