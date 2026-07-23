"""Shared Metro Cart brand assets and markup."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

BRAND_NAME = "Metro Cart"
_LOGO_PATH = Path(__file__).resolve().parent.parent / "images" / "metro_cart_logo.png"

# Shared Plotly / chart palette (blue-first)
MC_CHART_COLORS = ["#2563eb", "#0ea5e9", "#047857", "#b45309", "#9ca3af", "#1e40af"]
MC_CHART_SCALE = ["#dbeafe", "#2563eb", "#1e40af"]


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    if not _LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def brand_mark_html(*, size: int = 28) -> str:
    """Small inline logo suitable for headers and sidebars."""
    uri = _logo_data_uri()
    if not uri:
        return ""
    return (
        f'<img class="mc-brand-mark" src="{uri}" width="{size}" height="{size}" '
        f'alt="{BRAND_NAME}" />'
    )


def brand_wordmark_html(*, size: int = 28, name: str | None = None) -> str:
    """Logo + Metro Cart wordmark used across portals."""
    label = name or BRAND_NAME
    return (
        f'<span class="mc-brand-wordmark">'
        f"{brand_mark_html(size=size)}"
        f'<span class="mc-brand-name">{label}</span>'
        f"</span>"
    )
