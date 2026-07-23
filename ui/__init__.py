"""Shared UI helpers for Streamlit.

Expose styling helpers used across portal pages to keep a consistent look.
"""

from .style import apply_theme, render_app_shell
from .customer_login import (
    apply_customer_theme,
    apply_customer_login_theme,
    render_customer_shell,
)

__all__ = [
    "apply_theme",
    "render_app_shell",
    "apply_customer_theme",
    "apply_customer_login_theme",
    "render_customer_shell",
]
