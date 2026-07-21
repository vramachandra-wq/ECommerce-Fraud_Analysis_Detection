import streamlit as st


def apply_theme():
    """Inject a minimal, professional dashboard theme with red accents.

    IMPORTANT: Streamlit does NOT set a `data-theme` attribute on <html>/<body>,
    so CSS rules like `html[data-theme="dark"] { ... }` never match anything —
    that was the root cause of text disappearing when switching modes: the
    dark-mode overrides simply never fired.

    Instead, Streamlit exposes the *active* theme (light or dark, whichever the
    viewer has selected) as CSS custom properties on the page: `--background-color`,
    `--secondary-background-color`, `--text-color`, and `--primary-color`. These
    update live the moment the user flips the theme in Settings, with no extra
    JS or attribute-detection needed. We alias our own variable names to them so
    the rest of the app (and this file) can keep using `var(--card-bg)`,
    `var(--text)`, etc., and it will automatically stay correct in both modes.

    Should be called after `st.set_page_config()` in the top-level app.
    """
    css = r"""
    <style>
    :root {
      /* Alias our variable names to Streamlit's native theme variables so
         colors always match the viewer's active light/dark selection. */
      --bg: var(--background-color);
      --card-bg: var(--secondary-background-color);
      --text: var(--text-color);
      --primary-blue: #1f56ff;
      --primary-red: #be1e2d;
      --accent: var(--primary-color, var(--primary-red));
      /* Neutral, semi-transparent gray reads correctly on both a light and a
         dark background, so it does not need a separate light/dark value. */
      --border: rgba(128, 140, 158, 0.35);
      --radius: 10px;
    }

    .stApp {
      font-family: Inter, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
      line-height: 1.45;
      color: var(--text);
    }

    /* Muted/secondary text: dim the current text color instead of hardcoding
       a gray hex, so it stays legible on both themes. */
    .app-shell__brand-tagline,
    .stCaption,
    small {
      color: var(--text) !important;
      opacity: 0.68;
    }

    .app-shell {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 16px;
      align-items: center;
      margin-bottom: 24px;
    }

    .app-shell__brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 0;
    }

    .app-shell__brand-name {
      font-size: 1.2rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      color: var(--primary-red);
      margin: 0;
    }

    .app-shell__brand-tagline {
      margin: 0;
      font-size: 0.95rem;
    }

    .app-shell__actions {
      justify-self: end;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .section-title {
      font-size: 1.1rem;
      margin-bottom: 8px;
      font-weight: 600;
      color: var(--text);
    }

    .dashboard-card, .stCard, .stContainer {
      background: var(--card-bg) !important;
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      padding: 18px !important;
      box-shadow: none !important;
      color: var(--text) !important;
    }

    /* Buttons: rely on Streamlit's own theming for the base look, just keep
       our accent + radius consistent, and force readable label color. */
    button[kind="primary"],
    .stButton button[kind="primary"] {
      background-color: var(--accent) !important;
      border-color: var(--accent) !important;
      color: #ffffff !important;
      border-radius: 8px !important;
      padding: 8px 14px !important;
    }
    button[kind="primary"] * {
      color: #ffffff !important;
    }

    button[kind="secondary"],
    .stButton button[kind="secondary"] {
      background-color: transparent !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
      border-radius: 8px !important;
      padding: 8px 14px !important;
    }
    button[kind="secondary"] * {
      color: var(--text) !important;
    }

    .stMetric {
      padding: 12px 14px !important;
      border: 1px solid var(--border) !important;
      border-radius: 12px !important;
      background: var(--card-bg) !important;
    }
    .stMetric label, .stMetric [data-testid="stMetricValue"] {
      color: var(--text) !important;
    }

    /* Dataframes: force borders/background to follow the active theme so
       grid lines don't vanish (or clash) after a theme switch. */
    .stDataFrame > div:first-child,
    .stDataFrame div[role="grid"],
    .stDataFrame div[role="rowheader"],
    .stDataFrame div[role="gridcell"],
    .stDataFrame div[role="row"] {
      border-radius: 10px !important;
      overflow: hidden;
      border: 1px solid var(--border) !important;
      background: var(--card-bg) !important;
      color: var(--text) !important;
    }

    .status-badge {
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.85rem;
    }

    /* These status colors use a fixed background + fixed contrasting text
       color (not theme variables) on purpose — the badge needs to stay
       legible against its own colored chip regardless of the surrounding
       page theme. */
    .status-PENDING_REVIEW {
      background: var(--primary-red);
      color: #ffffff;
    }

    .status-ON_HOLD {
      background: var(--primary-blue);
      color: #ffffff;
    }

    /* Form labels, markdown body text, plain text: always follow the active
       theme's text color explicitly, since Streamlit's own defaults can be
       inconsistent across custom-styled containers. */
    label, .stMarkdown, .stText, p, span, h1, h2, h3, h4, h5, h6 {
      color: var(--text);
    }

    /* Inputs: force text/placeholder colors to track the theme so typed text
       and placeholder hints never end up the same color as the field
       background (the previous bug: placeholders were hardcoded near-white,
       which made them invisible in light mode). */
    .stApp input,
    .stApp textarea,
    .stApp select,
    .stApp .stTextInput input,
    .stApp .stTextArea textarea,
    .stApp .stNumberInput input,
    .stApp .stDateInput input {
      color: var(--text) !important;
      -webkit-text-fill-color: var(--text) !important;
      background-color: var(--card-bg) !important;
    }

    .stApp input::placeholder,
    .stApp textarea::placeholder {
      color: var(--text) !important;
      opacity: 0.55 !important;
      -webkit-text-fill-color: var(--text) !important;
    }

    /* Sidebar: match card background and force readable, full-opacity text
       and icons regardless of theme. */
    section[data-testid="stSidebar"] {
      background: var(--card-bg) !important;
      color: var(--text) !important;
    }
    section[data-testid="stSidebar"] * {
      color: var(--text) !important;
      opacity: 1 !important;
      -webkit-text-fill-color: var(--text) !important;
    }
    section[data-testid="stSidebar"] svg {
      fill: var(--text) !important;
      stroke: var(--text) !important;
    }

    /* Links */
    .stApp a, .stApp .stMarkdown a {
      color: var(--primary-blue);
    }

    @media (max-width: 768px) {
      .app-shell {
        grid-template-columns: 1fr;
      }
    }

    /* Centered login card for customer / analyst login screens */
    .login-panel {
      max-width: 480px;
      margin: 0 auto 2rem auto;
      padding: 1.5rem 1.75rem;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--card-bg);
    }

    /* Sidebar navigation radio: pill-style active state */
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
      border-radius: 8px !important;
      padding: 0.45rem 0.75rem !important;
      margin-bottom: 0.25rem !important;
      border: 1px solid transparent !important;
      transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
      background-color: rgba(190, 30, 45, 0.12) !important;
      border-color: var(--primary-red) !important;
      font-weight: 600 !important;
    }

    /* Section headings inside portals */
    h4, h3 {
      letter-spacing: -0.01em;
    }

    /* Language selector: compact pill in top-right */
    div[data-testid="stSelectbox"]:has(select[aria-label]) {
      font-size: 0.9rem;
    }
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def render_app_shell(title: str, subtitle: str | None = None, actions: list[str] | None = None):
    """Render a minimal top app shell for consistent page headers."""
    actions = actions or []
    cols = st.columns([1, 0.3])
    with cols[0]:
        st.markdown(
            f"""
            <div class="app-shell">
              <div>
                <div class="app-shell__brand">
                  <span class="app-shell__brand-name">{title}</span>
                </div>
                {f'<p class="app-shell__brand-tagline">{subtitle}</p>' if subtitle else ''}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cols[1]:
        if actions:
            buttons = "".join([f'<span>{action}</span>' for action in actions])
            st.markdown(f"<div class=\"app-shell__actions\">{buttons}</div>", unsafe_allow_html=True)
