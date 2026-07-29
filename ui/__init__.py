"""Shared UI helpers — translation catalog for API / static portals."""

from .i18n import TRANSLATIONS, cur_sym, format_duration_minutes, set_lang, t

__all__ = [
    "TRANSLATIONS",
    "t",
    "cur_sym",
    "format_duration_minutes",
    "set_lang",
]
