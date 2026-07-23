"""Shared Metro Cart design tokens (blue / white enterprise theme)."""

# Injected inside <style> blocks via f-strings / concatenation.
METRO_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@"
    "0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');"
)

# CSS custom properties — keep --mc-coral / --mc-peach names for compatibility;
# values are blue/white.
ROOT_TOKENS_CSS = """
:root {
  --mc-bg: #eef2f7;
  --mc-surface: #ffffff;
  --mc-peach: #e8f0fe;
  --mc-art: #dbe7f7;
  --mc-coral: #2563eb;
  --mc-coral-deep: #1e40af;
  --mc-text: #111827;
  --mc-muted: #6b7280;
  --mc-label: #374151;
  --mc-border: rgba(30, 30, 30, 0.08);
  --mc-radius: 18px;
  --mc-radius-control: 14px;
  --mc-radius-input: 10px;
  --mc-shadow: 0 18px 48px rgba(30, 30, 30, 0.08);
  --mc-shadow-sm: 0 8px 20px rgba(30, 30, 30, 0.05);
  --mc-shadow-btn: 0 10px 24px rgba(37, 99, 235, 0.28);
  --mc-font: "DM Sans", "Segoe UI", sans-serif;
  --mc-control-height: 2.75rem;
  --mc-input-height: 2.55rem;
  --bg: var(--mc-bg);
  --card-bg: var(--mc-surface);
  --text: var(--mc-text);
  --brand: var(--mc-coral);
  --brand-deep: var(--mc-coral-deep);
  --hold: #0284c8;
  --ok: #047857;
  --warn: #b45309;
  --danger: #dc2626;
  --accent: var(--mc-coral);
  --border: var(--mc-border);
  --radius: var(--mc-radius);
}
"""

DIALOG_CSS = """
/* Streamlit dialogs / modals */
div[data-testid="stModal"] > div,
div[role="dialog"] {
  font-family: var(--mc-font) !important;
  background: var(--mc-surface) !important;
  border: 1px solid var(--mc-border) !important;
  border-radius: var(--mc-radius) !important;
  box-shadow: var(--mc-shadow) !important;
  color: var(--mc-text) !important;
}
div[data-testid="stModal"] h1,
div[data-testid="stModal"] h2,
div[role="dialog"] h1,
div[role="dialog"] h2 {
  font-family: var(--mc-font) !important;
  color: var(--mc-text) !important;
  letter-spacing: -0.02em !important;
  font-weight: 700 !important;
}
"""
