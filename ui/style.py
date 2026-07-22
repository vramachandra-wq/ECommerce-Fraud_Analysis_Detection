"""Shared Streamlit theme and page chrome for Metro Cart portals."""

import streamlit as st


def apply_theme():
    """Inject the Metro Cart visual system (light/dark aware via Streamlit vars).

    Call after ``st.set_page_config()``. Does not change app behavior.
    """
    css = r"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@600;700&display=swap');

    :root {
      --bg: var(--background-color);
      --card-bg: var(--secondary-background-color);
      --text: var(--text-color);
      --brand: #b91c1c;
      --brand-deep: #7f1d1d;
      --hold: #1d4ed8;
      --ok: #047857;
      --warn: #b45309;
      --accent: var(--primary-color, var(--brand));
      --border: rgba(100, 116, 139, 0.28);
      --radius: 12px;
      --shadow-soft: 0 1px 0 rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.06);
      --font-ui: "IBM Plex Sans", "Segoe UI", sans-serif;
      --font-display: "IBM Plex Serif", Georgia, serif;
    }

    /* Atmosphere: subtle diagonal wash (not flat, not purple) */
    .stApp {
      font-family: var(--font-ui) !important;
      line-height: 1.5;
      color: var(--text);
      background:
        radial-gradient(1200px 500px at 8% -10%, rgba(185, 28, 28, 0.07), transparent 55%),
        radial-gradient(900px 420px at 100% 0%, rgba(29, 78, 216, 0.06), transparent 50%),
        linear-gradient(180deg, color-mix(in srgb, var(--bg) 92%, #94a3b8 8%) 0%, var(--bg) 42%, var(--bg) 100%) !important;
    }

    .stApp h1, .stApp h2, .stApp h3 {
      font-family: var(--font-display) !important;
      letter-spacing: -0.01em;
      font-weight: 700 !important;
    }

    .app-shell__brand-tagline,
    .stCaption,
    small {
      color: var(--text) !important;
      opacity: 0.68;
    }

    /* Top brand shell */
    .app-shell {
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
      margin: 0 0 1.25rem 0;
      padding: 1.1rem 1.25rem 1.15rem;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      background:
        linear-gradient(135deg, color-mix(in srgb, var(--card-bg) 88%, #b91c1c 12%) 0%, var(--card-bg) 48%, var(--card-bg) 100%);
      box-shadow: var(--shadow-soft);
      position: relative;
      overflow: hidden;
    }
    .app-shell::before {
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 5px;
      background: linear-gradient(180deg, var(--brand) 0%, var(--brand-deep) 100%);
    }
    .app-shell__brand {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-left: 8px;
    }
    .app-shell__brand-name {
      font-family: var(--font-display);
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--brand);
      margin: 0;
      line-height: 1.2;
    }
    .app-shell__brand-tagline {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 500;
    }

    .section-title {
      font-size: 1.12rem;
      margin-bottom: 8px;
      font-weight: 600;
      color: var(--text);
    }

    /* Cards / bordered containers */
    .dashboard-card,
    div[data-testid="stVerticalBlockBorderWrapper"] {
      background: var(--card-bg) !important;
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      box-shadow: var(--shadow-soft) !important;
    }
    .dashboard-card {
      padding: 1.15rem 1.25rem !important;
      margin-bottom: 1rem;
      color: var(--text) !important;
    }

    /* Primary / secondary buttons */
    button[kind="primary"],
    .stButton button[kind="primary"] {
      background: linear-gradient(180deg, #dc2626 0%, var(--brand) 100%) !important;
      border: 1px solid var(--brand-deep) !important;
      color: #ffffff !important;
      border-radius: 10px !important;
      padding: 0.5rem 1rem !important;
      font-weight: 600 !important;
      letter-spacing: 0.01em;
      box-shadow: 0 1px 0 rgba(127, 29, 29, 0.25) !important;
      transition: transform 0.12s ease, filter 0.12s ease;
    }
    button[kind="primary"]:hover {
      filter: brightness(1.05);
      transform: translateY(-1px);
    }
    button[kind="primary"] * {
      color: #ffffff !important;
    }

    button[kind="secondary"],
    .stButton button[kind="secondary"] {
      background-color: color-mix(in srgb, var(--card-bg) 80%, transparent) !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
      border-radius: 10px !important;
      padding: 0.5rem 1rem !important;
      font-weight: 560 !important;
    }
    button[kind="secondary"] * {
      color: var(--text) !important;
    }

    /* Metrics as quiet KPI tiles */
    div[data-testid="stMetric"] {
      padding: 0.9rem 1rem !important;
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--card-bg) 92%, #fff 8%), var(--card-bg)) !important;
      box-shadow: var(--shadow-soft) !important;
      border-left: 4px solid var(--brand) !important;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--text) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      font-family: var(--font-display) !important;
      font-weight: 700 !important;
    }

    /* Dataframes */
    .stDataFrame > div:first-child,
    .stDataFrame div[role="grid"] {
      border-radius: var(--radius) !important;
      overflow: hidden;
      border: 1px solid var(--border) !important;
      background: var(--card-bg) !important;
      color: var(--text) !important;
      box-shadow: var(--shadow-soft);
    }

    /* Status chips (fixed contrast on purpose) */
    .status-badge {
      font-weight: 700;
      padding: 0.28rem 0.7rem;
      border-radius: 999px;
      font-size: 0.8rem;
      letter-spacing: 0.02em;
      display: inline-block;
      vertical-align: middle;
    }
    .status-PENDING_REVIEW {
      background: #b45309;
      color: #fff7ed;
      border: 1px solid rgba(180, 83, 9, 0.35);
    }
    .status-ON_HOLD {
      background: var(--hold);
      color: #eff6ff;
      border: 1px solid rgba(29, 78, 216, 0.35);
    }
    .status-APPROVED {
      background: var(--ok);
      color: #ecfdf5;
      border: 1px solid rgba(4, 120, 87, 0.35);
    }
    .status-REJECTED {
      background: var(--brand);
      color: #fef2f2;
      border: 1px solid rgba(185, 28, 28, 0.35);
    }

    label, .stMarkdown, .stText, p, span, h1, h2, h3, h4, h5, h6 {
      color: var(--text);
    }

    /* Inputs */
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
      border-radius: 10px !important;
    }
    .stApp input::placeholder,
    .stApp textarea::placeholder {
      color: var(--text) !important;
      opacity: 0.5 !important;
      -webkit-text-fill-color: var(--text) !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--card-bg) 90%, #b91c1c 10%) 0%, var(--card-bg) 28%, var(--card-bg) 100%) !important;
      color: var(--text) !important;
      border-right: 1px solid var(--border) !important;
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
    section[data-testid="stSidebar"] .stRadio label {
      border-radius: 10px !important;
      padding: 0.35rem 0.5rem !important;
    }

    /* Dividers */
    hr {
      border: none !important;
      border-top: 1px solid var(--border) !important;
      margin: 1.25rem 0 !important;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
      border-radius: var(--radius) !important;
      border: 1px solid var(--border) !important;
    }

    /* Login / narrow forms feel more composed */
    div[data-testid="stForm"] {
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      padding: 1.15rem 1.25rem 1rem !important;
      background: var(--card-bg) !important;
      box-shadow: var(--shadow-soft) !important;
    }

    .stApp a, .stApp .stMarkdown a {
      color: var(--hold);
    }

    /* Language toggle: keep it quiet in the corner */
    div[data-testid="stSelectbox"]:has(#_lang_selector),
    div[data-testid="stSelectbox"]:has([aria-label="Language"]),
    div[data-testid="stSelectbox"]:has([aria-label="ภาษา"]) {
      max-width: 11rem;
      margin-left: auto;
    }

    @media (max-width: 768px) {
      .app-shell__brand-name { font-size: 1.3rem; }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_app_shell(title: str, subtitle: str | None = None, actions: list[str] | None = None):
    """Render the top brand shell. Visual chrome only."""
    actions = actions or []
    tagline = f'<p class="app-shell__brand-tagline">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="app-shell">
          <div class="app-shell__brand">
            <span class="app-shell__brand-name">{title}</span>
            {tagline}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if actions:
        st.markdown(
            "<div class=\"app-shell__actions\">"
            + "".join(f"<span>{action}</span>" for action in actions)
            + "</div>",
            unsafe_allow_html=True,
        )
