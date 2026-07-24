"""UTC time helpers — single convention for portals and APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def utcnow_naive() -> datetime:
    """Current UTC time as a naive datetime (matches TIMESTAMP columns + DB session UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_utc(value: Any, *, with_suffix: bool = True) -> str:
    """
    Format a timestamp for UI display in UTC.

    Accepts datetime, date, or common string forms. Naive values are treated as UTC.
    """
    if value is None or value == "":
        return "—"

    dt: Optional[datetime] = None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "nat"}:
            return "—"
        # Normalize space separator; strip fractional noise for parsing
        cleaned = text.replace("T", " ").replace("Z", "").replace("z", "")
        if "+" in cleaned[10:]:
            cleaned = cleaned.split("+", 1)[0].strip()
        elif cleaned.count("-") > 2 and " " in cleaned:
            # e.g. 2026-07-24 14:40:36.327914-00
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(cleaned[:26].rstrip(), fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return text

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    stamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    return f"{stamp} UTC" if with_suffix else stamp
