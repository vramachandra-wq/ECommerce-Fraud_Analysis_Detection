"""Customer portal visual system (login + authenticated checkout).

Matches the analyst portal Matx theme: Roboto, navy sidebar accents,
#1976d2 primary, #f5f6fa surface, white cards.
"""

import streamlit as st

from ui.brand import brand_wordmark_html
from ui.tokens import DIALOG_CSS

_CUSTOMER_FONT = (
    "@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');"
)


def apply_customer_theme() -> None:
    """Base theme for the entire customer app (login + portal)."""
    css = f"""
    <style>
    {_CUSTOMER_FONT}
    {DIALOG_CSS}

    :root {{
      --mc-bg: #f5f6fa;
      --mc-surface: #ffffff;
      --mc-peach: #e3f2fd;
      --mc-art: #1a2038;
      --mc-coral: #1976d2;
      --mc-coral-deep: #1565c0;
      --mc-text: #2c3345;
      --mc-text-strong: #1a2038;
      --mc-muted: #8b95a8;
      --mc-label: #2c3345;
      --mc-border: #e6e9f0;
      --mc-radius: 10px;
      --mc-shadow: 0 2px 8px rgba(26, 32, 56, 0.06);
      --mc-shadow-btn: 0 4px 12px rgba(25, 118, 210, 0.28);
      --mc-font: Roboto, system-ui, sans-serif;
    }}

    .stApp {{
      font-family: var(--mc-font) !important;
      background: var(--mc-bg) !important;
      color: var(--mc-text) !important;
    }}

    /* Keep Streamlit chrome from covering the brand shell / language toggle */
    header[data-testid="stHeader"] {{
      background: transparent !important;
      box-shadow: none !important;
    }}
    div[data-testid="stToolbar"] {{
      background: transparent !important;
    }}

    .stApp [data-testid="stAppViewContainer"] > section {{
      padding-top: 0.75rem !important;
    }}

    .stApp [data-testid="stMainBlockContainer"] {{
      max-width: 1100px !important;
      padding-top: 2.75rem !important;
    }}

    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
      font-family: var(--mc-font) !important;
      color: var(--mc-text-strong) !important;
      letter-spacing: 0.01em;
      font-weight: 700 !important;
    }}

    /* Avoid styling all spans — that breaks Material icon ligatures
       (password "visibility" control rendered as truncated "visibili"). */
    .stApp p, .stApp label, .stApp .stMarkdown,
    .stApp [data-testid="stMarkdownContainer"] {{
      font-family: var(--mc-font) !important;
    }}
    .stApp [data-testid="stIconMaterial"],
    .stApp span[data-testid="stIconMaterial"],
    .stApp [data-testid="stTextInput"] button,
    .stApp [data-testid="stTextInput"] button span {{
      font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
      letter-spacing: normal !important;
      text-transform: none !important;
      -webkit-text-fill-color: currentColor !important;
    }}

    .stCaption, small {{
      color: var(--mc-muted) !important;
      opacity: 1 !important;
    }}

    /* Brand shell (authenticated) — Matx-style white card */
    .customer-portal-shell {{
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      margin: 0 0 1.1rem 0;
      padding: 1.25rem 1.4rem 1.15rem;
      background: var(--mc-surface);
      border-radius: var(--mc-radius);
      box-shadow: var(--mc-shadow);
      border: 1px solid var(--mc-border);
      position: relative;
      overflow: hidden;
    }}
    .customer-portal-shell::before {{
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 4px;
      background: linear-gradient(180deg, #42a5f5, #1976d2);
    }}
    .customer-portal-logo {{
      color: var(--mc-text-strong);
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      margin: 0;
      padding-left: 0.65rem;
    }}
    .mc-brand-wordmark {{
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
    }}
    .mc-brand-mark {{
      display: block;
      width: 1.75rem;
      height: 1.75rem;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.25);
    }}
    .mc-brand-name {{
      color: inherit;
      font: inherit;
      letter-spacing: inherit;
    }}
    .customer-portal-welcome {{
      color: var(--mc-muted);
      font-size: 0.9rem;
      margin: 0;
      padding-left: 0.65rem;
    }}
    .customer-portal-title {{
      color: var(--mc-text-strong);
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      line-height: 1.2;
      margin: 0.15rem 0 0;
      padding-left: 0.65rem;
    }}

    .customer-section-title {{
      color: var(--mc-text-strong);
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      margin: 0.15rem 0 0.85rem;
    }}
    .mc-spacer-sm {{
      height: 0.75rem;
    }}

    /* Checkout section cards breathe a bit */
    .stApp:has(.customer-portal-shell) div[data-testid="stVerticalBlockBorderWrapper"] {{
      margin-bottom: 0.85rem !important;
    }}

    /* Cards / bordered blocks */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: var(--mc-radius) !important;
      box-shadow: var(--mc-shadow) !important;
    }}

    /* Inputs — soft accent fill like portal */
    .stApp input,
    .stApp textarea,
    .stApp .stTextInput input,
    .stApp .stTextArea textarea,
    .stApp .stNumberInput input,
    .stApp .stDateInput input {{
      background: var(--mc-peach) !important;
      border: 1px solid transparent !important;
      border-radius: 8px !important;
      min-height: 2.55rem !important;
      color: var(--mc-text) !important;
      -webkit-text-fill-color: var(--mc-text) !important;
      box-shadow: none !important;
    }}
    .stApp input:focus,
    .stApp textarea:focus {{
      border-color: var(--mc-coral) !important;
      box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.18) !important;
    }}
    .stApp input:disabled,
    .stApp .stTextInput input:disabled {{
      background: #eef0f5 !important;
      color: var(--mc-muted) !important;
      -webkit-text-fill-color: var(--mc-muted) !important;
    }}
    .stApp label {{
      font-size: 0.82rem !important;
      font-weight: 500 !important;
      color: var(--mc-label) !important;
    }}
    .stApp input::placeholder,
    .stApp textarea::placeholder {{
      color: var(--mc-muted) !important;
      opacity: 1 !important;
      -webkit-text-fill-color: var(--mc-muted) !important;
    }}

    /* Select / number chrome (exclude language dropdown) */
    .stApp div[data-testid="stSelectbox"]:not([class*="st-key-_lang_selector"]) div[data-baseweb="select"] > div {{
      background: var(--mc-peach) !important;
      border-color: transparent !important;
      border-radius: 8px !important;
    }}
    .stApp div[data-testid="stSelectbox"]:not([class*="st-key-_lang_selector"]) div[data-baseweb="select"] > div:focus-within {{
      border-color: var(--mc-coral) !important;
      box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.18) !important;
    }}

    /* Primary CTA — portal accent blue */
    button[kind="primary"],
    .stButton button[kind="primary"],
    button[kind="primaryFormSubmit"] {{
      background: var(--mc-coral) !important;
      border: none !important;
      border-radius: 8px !important;
      min-height: 2.65rem !important;
      padding: 0.5rem 1.1rem !important;
      font-weight: 700 !important;
      letter-spacing: 0.02em !important;
      color: #ffffff !important;
      box-shadow: var(--mc-shadow-btn) !important;
      transition: transform 0.12s ease, filter 0.12s ease, background 0.12s ease;
    }}
    button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover {{
      filter: brightness(1.05);
      transform: translateY(-1px);
      background: var(--mc-coral-deep) !important;
    }}
    button[kind="primary"] *,
    button[kind="primaryFormSubmit"] * {{
      color: #ffffff !important;
    }}

    button[kind="secondary"],
    .stButton button[kind="secondary"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      color: var(--mc-text) !important;
      border-radius: 8px !important;
      font-weight: 600 !important;
    }}

    /* Metrics */
    div[data-testid="stMetric"] {{
      padding: 0.95rem 1.05rem !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: var(--mc-radius) !important;
      background: var(--mc-surface) !important;
      box-shadow: var(--mc-shadow) !important;
      border-left: 4px solid var(--mc-coral) !important;
    }}
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
      color: var(--mc-text) !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
      font-family: var(--mc-font) !important;
      font-weight: 700 !important;
      color: var(--mc-text-strong) !important;
    }}

    /* Banner image soft corners */
    .stApp [data-testid="stImage"] img {{
      border-radius: 10px !important;
    }}

    hr {{
      border: none !important;
      border-top: 1px solid var(--mc-border) !important;
      margin: 1.15rem 0 !important;
    }}

    div[data-testid="stAlert"] {{
      border-radius: 10px !important;
      border: 1px solid var(--mc-border) !important;
    }}

    div[data-testid="stForm"] {{
      border: none !important;
      box-shadow: none !important;
      background: transparent !important;
      padding: 0 !important;
    }}

    .stApp a, .stApp .stMarkdown a {{
      color: var(--mc-coral);
    }}

    /* Language dropdown */
    div[class*="st-key-_lang_selector"][data-testid="stSelectbox"],
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] {{
      width: 100% !important;
      min-width: 12.5rem !important;
      max-width: 16rem !important;
      margin-left: auto !important;
    }}
    div[class*="st-key-_lang_selector"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] div[data-baseweb="select"] > div {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      box-shadow: var(--mc-shadow) !important;
      border-radius: 8px !important;
      min-height: 2.6rem !important;
      padding-left: 0.9rem !important;
      padding-right: 0.65rem !important;
    }}
    div[class*="st-key-_lang_selector"] div[data-baseweb="select"] span,
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] div[data-baseweb="select"] span {{
      white-space: nowrap !important;
      overflow: visible !important;
      text-overflow: clip !important;
      font-weight: 600 !important;
      color: var(--mc-text) !important;
    }}

    /* Align header actions with the white brand shell */
    div[data-testid="stHorizontalBlock"]:has(.customer-portal-shell) {{
      align-items: center !important;
      gap: 0.65rem !important;
      margin-top: 0.25rem !important;
    }}
    div[data-testid="column"]:has([class*="st-key-_lang_selector"]) {{
      display: flex !important;
      align-items: center !important;
      justify-content: flex-end !important;
    }}

    @media (max-width: 768px) {{
      .customer-portal-title {{ font-size: 1.35rem; }}
      .stApp [data-testid="stMainBlockContainer"] {{
        max-width: 100% !important;
      }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def apply_customer_login_theme() -> None:
    """Extra layout rules for the unauthenticated split-screen login."""
    css = r"""
    <style>
    .stApp:has(.customer-login-marker) [data-testid="stAppViewContainer"] > section {
      padding: 0 1.25rem 1.5rem !important;
      max-width: 100% !important;
    }
    .stApp:has(.customer-login-marker) [data-testid="stMainBlockContainer"] {
      max-width: 1080px !important;
      padding-top: 2.5rem !important;
    }

    .stApp:has(.customer-login-marker) div[data-testid="stHorizontalBlock"]:has(.customer-login-row) {
      align-items: stretch !important;
      gap: 0 !important;
      min-height: 620px;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) {
      background: #ffffff !important;
      border-radius: 10px 0 0 10px !important;
      box-shadow: 0 2px 8px rgba(26, 32, 56, 0.06) !important;
      border: 1px solid #e6e9f0 !important;
      border-right: none !important;
      padding: 2.25rem 2.35rem 2rem !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: center !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-art-host) {
      background: #1a2038 !important;
      border-radius: 0 10px 10px 0 !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      padding: 2rem 1.5rem !important;
      border: 1px solid #e6e9f0 !important;
      border-left: none !important;
    }

    .customer-login-logo {
      color: #1a2038;
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      margin: 0 0 1.75rem 0;
    }
    .customer-login-logo .mc-brand-wordmark {
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
    }
    .customer-login-logo .mc-brand-mark {
      display: block;
      width: 2rem;
      height: 2rem;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.35);
    }
    .customer-login-logo .mc-brand-name {
      color: inherit;
      font: inherit;
      letter-spacing: inherit;
    }
    .customer-login-welcome {
      color: var(--mc-muted, #8b95a8);
      font-size: 0.9rem;
      margin: 0 0 0.35rem 0;
    }
    .customer-login-title {
      color: #1a2038;
      font-size: 2.15rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      line-height: 1.15;
      margin: 0 0 1.65rem 0;
    }
    .customer-login-demo {
      margin-top: 1.1rem;
      text-align: center;
      color: var(--mc-muted, #8b95a8);
      font-size: 0.78rem;
      line-height: 1.45;
    }
    .customer-login-art-host {
      display: none;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-art-host) [data-testid="stImage"] {
      width: 100%;
      max-width: 380px;
      margin: 0 auto;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-art-host) [data-testid="stImage"] img {
      width: 100%;
      height: auto;
      object-fit: contain;
      border-radius: 10px;
      filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.25));
    }

    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) div[data-testid="stForm"] {
      border: none !important;
      box-shadow: none !important;
      background: transparent !important;
      padding: 0 !important;
      margin: 0 !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) label {
      font-size: 0.82rem !important;
      font-weight: 500 !important;
      color: #2c3345 !important;
      margin-bottom: 0.35rem !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) input {
      background: #e3f2fd !important;
      border: 1px solid transparent !important;
      border-radius: 8px !important;
      min-height: 2.55rem !important;
      padding: 0.65rem 0.9rem !important;
      color: #2c3345 !important;
      -webkit-text-fill-color: #2c3345 !important;
      box-shadow: none !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) input:focus {
      border-color: #1976d2 !important;
      box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.18) !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) button[kind="primaryFormSubmit"] {
      background: #1976d2 !important;
      border: none !important;
      border-radius: 8px !important;
      min-height: 2.65rem !important;
      font-weight: 700 !important;
      letter-spacing: 0.02em !important;
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.28) !important;
      margin-top: 0.35rem !important;
    }
    .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) button[kind="primaryFormSubmit"]:hover {
      filter: brightness(1.05);
      transform: translateY(-1px);
      background: #1565c0 !important;
    }

    /* Login: language control stays above the split card */
    .stApp:has(.customer-login-marker) div[data-testid="stHorizontalBlock"]:has([class*="st-key-_lang_selector"]) {
      margin-bottom: 0.35rem !important;
    }

    @media (max-width: 900px) {
      .stApp:has(.customer-login-marker) div[data-testid="stHorizontalBlock"]:has(.customer-login-row) {
        min-height: auto;
      }
      .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-art-host) {
        display: none !important;
      }
      .stApp:has(.customer-login-marker) div[data-testid="column"]:has(.customer-login-card-inner) {
        border-radius: 10px !important;
        border-right: 1px solid #e6e9f0 !important;
      }
      .customer-login-title {
        font-size: 1.85rem;
      }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_customer_shell(*, logo: str, welcome: str, title: str | None = None) -> None:
    """Authenticated portal brand header in the login visual language."""
    title_html = f'<p class="customer-portal-title">{title}</p>' if title else ""
    st.markdown(
        f"""
        <div class="customer-portal-shell">
          <p class="customer-portal-logo">{brand_wordmark_html(name=logo)}</p>
          <p class="customer-portal-welcome">{welcome}</p>
          {title_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_header(*, logo: str, welcome: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="customer-login-card-inner">
          <p class="customer-login-logo">{brand_wordmark_html(name=logo, size=32)}</p>
          <p class="customer-login-welcome">{welcome}</p>
          <h1 class="customer-login-title">{title}</h1>
        """,
        unsafe_allow_html=True,
    )


def render_login_close(*, demo_hint: str | None = None) -> None:
    hint = f'<p class="customer-login-demo">{demo_hint}</p>' if demo_hint else ""
    st.markdown(
        f"""
          {hint}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_illustration(image_path: str) -> None:
    st.markdown('<div class="customer-login-art-host" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.image(image_path, use_container_width=True)
