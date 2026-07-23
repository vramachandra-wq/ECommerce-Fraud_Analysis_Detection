"""Shared Streamlit theme and page chrome for Metro Cart portals.

Blue / white enterprise theme: DM Sans, cool gray-blue canvas, blue accent,
soft blue inputs, and white surfaces.
"""

import streamlit as st

from ui.brand import brand_wordmark_html
from ui.tokens import DIALOG_CSS, METRO_FONT_IMPORT, ROOT_TOKENS_CSS


def apply_theme():
    """Inject the Metro Cart visual system used across customer + analyst portals.

    Call after ``st.set_page_config()``. Does not change app behavior.
    """
    css = f"""
    <style>
    {METRO_FONT_IMPORT}
    {ROOT_TOKENS_CSS}
    {DIALOG_CSS}

    .stApp {{
      font-family: var(--mc-font) !important;
      line-height: 1.5;
      color: var(--mc-text) !important;
      background: var(--mc-bg) !important;
    }}

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
      max-width: 1400px !important;
      padding-top: 2.75rem !important;
    }}

    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
      font-family: var(--mc-font) !important;
      letter-spacing: -0.02em;
      font-weight: 700 !important;
      color: var(--mc-text) !important;
    }}

    /* Do not force font on all spans — breaks Material icon ligatures */
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

    .app-shell__brand-tagline,
    .stCaption,
    small {{
      color: var(--mc-muted) !important;
      opacity: 1 !important;
    }}

    /* Top brand shell — same language as customer portal */
    .app-shell {{
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      margin: 0 0 1.1rem 0;
      padding: 1.35rem 1.5rem 1.25rem;
      border-radius: var(--mc-radius);
      background: var(--mc-surface);
      box-shadow: var(--mc-shadow);
      border: none;
      position: relative;
      overflow: hidden;
    }}
    .app-shell::before {{
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 5px;
      background: var(--mc-coral);
    }}
    .app-shell__brand {{
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      padding-left: 0.65rem;
    }}
    .app-shell__brand-name {{
      font-family: var(--mc-font);
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--mc-coral);
      margin: 0;
      line-height: 1.2;
    }}
    .app-shell__brand .mc-brand-wordmark {{
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
    }}
    .app-shell__brand .mc-brand-mark {{
      display: block;
      width: 1.75rem;
      height: 1.75rem;
      border-radius: 8px;
      object-fit: cover;
      flex-shrink: 0;
    }}
    .app-shell__brand .mc-brand-name {{
      color: inherit;
      font: inherit;
      letter-spacing: inherit;
    }}
    .sidebar-brand {{
      display: flex;
      align-items: center;
      gap: 0.55rem;
      margin: 0.15rem 0 0.65rem;
      color: var(--mc-coral);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .sidebar-brand .mc-brand-mark {{
      width: 1.5rem;
      height: 1.5rem;
      border-radius: 7px;
    }}
    .app-shell__brand-tagline {{
      margin: 0;
      font-size: 0.95rem;
      font-weight: 500;
      color: var(--mc-muted) !important;
    }}

    .section-title {{
      font-size: 1.05rem;
      margin-bottom: 8px;
      font-weight: 700;
      color: var(--mc-text);
      letter-spacing: -0.01em;
    }}
    .page-heading {{
      font-family: var(--mc-font);
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--mc-text);
      margin: 0 0 0.35rem 0;
      line-height: 1.2;
    }}
    .mc-spacer-sm {{
      height: 0.75rem;
    }}

    /* Cards / bordered containers */
    .dashboard-card,
    div[data-testid="stVerticalBlockBorderWrapper"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: var(--mc-radius) !important;
      box-shadow: var(--mc-shadow) !important;
    }}
    .dashboard-card {{
      padding: 1.15rem 1.25rem !important;
      margin-bottom: 1rem;
      color: var(--mc-text) !important;
    }}

    /* Primary / secondary buttons — rounded squares */
    button[kind="primary"],
    .stButton button[kind="primary"],
    button[kind="primaryFormSubmit"] {{
      background: var(--mc-coral) !important;
      border: none !important;
      color: #ffffff !important;
      border-radius: var(--mc-radius-control) !important;
      min-height: var(--mc-control-height) !important;
      padding: 0.5rem 1.1rem !important;
      font-weight: 700 !important;
      letter-spacing: 0.04em;
      box-shadow: var(--mc-shadow-btn) !important;
      transition: transform 0.12s ease, filter 0.12s ease;
    }}
    button[kind="primary"]:hover,
    button[kind="primaryFormSubmit"]:hover {{
      filter: brightness(1.03);
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
      border-radius: var(--mc-radius-control) !important;
      min-height: var(--mc-control-height) !important;
      padding: 0.5rem 1rem !important;
      font-weight: 600 !important;
      box-shadow: none !important;
    }}
    button[kind="secondary"] * {{
      color: var(--mc-text) !important;
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
    }}

    /* Dataframes / data editors */
    .stDataFrame > div:first-child,
    .stDataFrame div[role="grid"],
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"],
    div[data-testid="stDataEditor"] > div {{
      border-radius: var(--mc-radius) !important;
      overflow: hidden;
      border: 1px solid var(--mc-border) !important;
      background: var(--mc-surface) !important;
      color: var(--mc-text) !important;
      box-shadow: var(--mc-shadow-sm);
    }}

    /* Status chips */
    .status-badge {{
      font-weight: 700;
      padding: 0.28rem 0.7rem;
      border-radius: 14px;
      font-size: 0.8rem;
      letter-spacing: 0.02em;
      display: inline-block;
      vertical-align: middle;
    }}
    .status-PENDING_REVIEW {{
      background: #b45309;
      color: #fff7ed;
      border: 1px solid rgba(180, 83, 9, 0.35);
    }}
    .status-ON_HOLD {{
      background: var(--hold);
      color: #f0f9ff;
      border: 1px solid rgba(2, 132, 200, 0.35);
    }}
    .status-APPROVED {{
      background: var(--ok);
      color: #ecfdf5;
      border: 1px solid rgba(4, 120, 87, 0.35);
    }}
    .status-REJECTED {{
      background: #dc2626;
      color: #fef2f2;
      border: 1px solid rgba(220, 38, 38, 0.35);
    }}

    label, .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6 {{
      color: var(--mc-text);
    }}
    .stApp label {{
      font-size: 0.82rem !important;
      font-weight: 500 !important;
      color: var(--mc-label) !important;
    }}

    /* Inputs — soft blue fill (form fields only; chatbot composer is reset below) */
    .stApp input,
    .stApp select,
    .stApp .stTextInput input,
    .stApp .stTextArea textarea,
    .stApp .stNumberInput input,
    .stApp .stDateInput input {{
      color: var(--mc-text) !important;
      -webkit-text-fill-color: var(--mc-text) !important;
      background: var(--mc-peach) !important;
      border: 1px solid transparent !important;
      border-radius: 10px !important;
      min-height: 2.55rem !important;
      box-shadow: none !important;
    }}
    /* Chat composer — compact single-row layout (no peach / no tall empty box) */
    .stApp div[data-testid="stChatInput"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: 14px !important;
      box-shadow: var(--mc-shadow) !important;
      padding: 0.4rem 0.55rem 0.4rem 0.85rem !important;
    }}
    .stApp div[data-testid="stChatInput"] > div,
    .stApp div[data-testid="stChatInput"] form,
    .stApp div[data-testid="stChatInput"] [data-testid="stChatInputContainer"],
    .stApp div[data-testid="stChatInput"] [data-baseweb="base-input"],
    .stApp div[data-testid="stChatInput"] [data-baseweb="textarea"] {{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      display: flex !important;
      flex-direction: row !important;
      align-items: center !important;
      gap: 0.5rem !important;
      min-height: 0 !important;
      height: auto !important;
      padding: 0 !important;
      margin: 0 !important;
    }}
    .stApp div[data-testid="stChatInput"] textarea,
    .stApp div[data-testid="stChatInput"] input,
    .stApp div[data-testid="stChatInput"] [contenteditable="true"] {{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      border-radius: 0 !important;
      color: var(--mc-text) !important;
      -webkit-text-fill-color: var(--mc-text) !important;
      flex: 1 1 auto !important;
      width: 100% !important;
      min-height: 1.5rem !important;
      height: 1.5rem !important;
      max-height: 4.5rem !important;
      line-height: 1.5rem !important;
      padding: 0 !important;
      margin: 0 !important;
      resize: none !important;
      overflow-y: auto !important;
    }}
    .stApp div[data-testid="stChatInput"] textarea:focus,
    .stApp div[data-testid="stChatInput"] input:focus {{
      border: none !important;
      box-shadow: none !important;
    }}
    .stApp div[data-testid="stChatInput"] button {{
      align-self: center !important;
      flex: 0 0 auto !important;
      min-height: 2rem !important;
      height: 2rem !important;
      width: 2rem !important;
      padding: 0 !important;
      margin: 0 !important;
      border-radius: 10px !important;
      box-shadow: none !important;
      transform: none !important;
    }}
    .stApp div[data-testid="stChatInput"] button:hover {{
      transform: none !important;
    }}
    .stApp input:focus,
    .stApp .stTextArea textarea:focus {{
      border-color: var(--mc-coral) !important;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
    }}
    .stApp input:disabled,
    .stApp .stTextInput input:disabled {{
      background: #f3f4f6 !important;
      color: #6b7280 !important;
      -webkit-text-fill-color: #6b7280 !important;
    }}
    .stApp input::placeholder,
    .stApp .stTextArea textarea::placeholder,
    .stApp div[data-testid="stChatInput"] textarea::placeholder {{
      color: var(--mc-muted) !important;
      opacity: 1 !important;
      -webkit-text-fill-color: var(--mc-muted) !important;
    }}
    .stApp div[data-testid="stSelectbox"]:not([class*="st-key-_lang_selector"]) div[data-baseweb="select"] > div {{
      background: var(--mc-peach) !important;
      border-color: transparent !important;
      border-radius: 10px !important;
    }}
    .stApp div[data-testid="stSelectbox"]:not([class*="st-key-_lang_selector"]) div[data-baseweb="select"] > div:focus-within {{
      border-color: var(--mc-coral) !important;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
      background: var(--mc-surface) !important;
      color: var(--mc-text) !important;
      border-right: 1px solid var(--mc-border) !important;
      overflow-x: hidden !important;
      box-shadow: 8px 0 24px rgba(30, 30, 30, 0.04);
    }}
    section[data-testid="stSidebar"]::before {{
      content: "";
      display: block;
      height: 4px;
      background: var(--mc-coral);
      margin: 0 0 0.75rem 0;
    }}
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {{
      color: var(--mc-text) !important;
      font-family: var(--mc-font) !important;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
      border-radius: 14px !important;
      padding: 0.45rem 0.65rem !important;
      background: transparent !important;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
      background: var(--mc-peach) !important;
    }}
    section[data-testid="stSidebar"] svg {{
      fill: var(--mc-text) !important;
      stroke: var(--mc-text) !important;
    }}

    hr {{
      border: none !important;
      border-top: 1px solid var(--mc-border) !important;
      margin: 1.25rem 0 !important;
    }}

    div[data-testid="stAlert"] {{
      border-radius: 14px !important;
      border: 1px solid var(--mc-border) !important;
    }}

    div[data-testid="stForm"] {{
      border: 1px solid var(--mc-border) !important;
      border-radius: var(--mc-radius) !important;
      padding: 1.25rem 1.35rem 1.1rem !important;
      background: var(--mc-surface) !important;
      box-shadow: var(--mc-shadow) !important;
    }}

    .stApp a, .stApp .stMarkdown a {{
      color: var(--mc-coral);
    }}

    /* Sidebar nav — selected item */
    section[data-testid="stSidebar"] .stRadio label:has(input:checked) {{
      background: var(--mc-peach) !important;
      border-left: 3px solid var(--mc-coral) !important;
      font-weight: 600 !important;
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: 14px !important;
      box-shadow: 0 8px 20px rgba(30, 30, 30, 0.04) !important;
    }}

    /* Tabs */
    button[data-baseweb="tab"] {{
      font-family: var(--mc-font) !important;
      font-weight: 600 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
      color: var(--mc-coral) !important;
      border-bottom-color: var(--mc-coral) !important;
    }}

    /* Chat messages default to assistant (left). User bubbles are custom HTML. */
    .stApp:has(.chatbot-shell) [data-testid="stStatusWidget"] {{
      display: none !important;
    }}
    .stApp:has(.chatbot-shell) div[data-testid="stChatMessage"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: 14px !important;
      box-shadow: 0 6px 16px rgba(30, 30, 30, 0.04) !important;
      margin: 0 0 0.85rem 0 !important;
      margin-left: 0 !important;
      margin-right: auto !important;
      padding: 0.85rem 1rem !important;
      max-width: 100% !important;
      width: 100% !important;
      flex-direction: row !important;
      justify-content: flex-start !important;
      text-align: left !important;
    }}
    .stApp:has(.chatbot-shell) div[data-testid="stChatMessage"] [data-testid="stChatMessageContent"],
    .stApp:has(.chatbot-shell) div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    .stApp:has(.chatbot-shell) div[data-testid="stChatMessage"] p {{
      text-align: left !important;
      color: var(--mc-text) !important;
    }}
    .mc-chat-row--user {{
      display: flex;
      justify-content: flex-end;
      width: 100%;
      margin: 0 0 0.85rem 0;
    }}
    .mc-chat-bubble--user {{
      max-width: min(78%, 42rem);
      background: var(--mc-coral);
      color: #ffffff;
      border-radius: 14px 14px 4px 14px;
      padding: 0.75rem 1rem;
      font-size: 0.95rem;
      font-weight: 500;
      line-height: 1.45;
      box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22);
      white-space: pre-wrap;
      word-break: break-word;
    }}

    div[data-testid="stChatMessage"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: 14px !important;
      box-shadow: 0 6px 16px rgba(30, 30, 30, 0.04) !important;
      margin-bottom: 0.65rem !important;
      padding: 0.85rem 1rem !important;
    }}

    /* Chatbot page chrome */
    .chatbot-topic-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      margin: 0.35rem 0 1rem 0;
    }}
    .chatbot-topic-chip {{
      display: inline-flex;
      align-items: center;
      padding: 0.28rem 0.7rem;
      border-radius: 14px;
      background: var(--mc-peach);
      color: var(--mc-label);
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      border: 1px solid rgba(37, 99, 235, 0.18);
    }}
    .chatbot-status {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.75rem;
      border-radius: 14px;
      font-size: 0.8rem;
      font-weight: 600;
      white-space: nowrap;
    }}
    .chatbot-status::before {{
      content: "";
      width: 0.5rem;
      height: 0.5rem;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .chatbot-status--ok {{
      background: #ecfdf5;
      color: #047857;
      border: 1px solid rgba(4, 120, 87, 0.22);
    }}
    .chatbot-status--ok::before {{
      background: #047857;
    }}
    .chatbot-status--err {{
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid rgba(220, 38, 38, 0.22);
    }}
    .chatbot-status--err::before {{
      background: #dc2626;
    }}
    .chatbot-empty {{
      background: var(--mc-surface);
      border: 1px solid var(--mc-border);
      border-radius: var(--mc-radius);
      box-shadow: var(--mc-shadow);
      padding: 1.35rem 1.4rem 1.2rem;
      margin: 0.25rem 0 1rem 0;
      position: relative;
      overflow: hidden;
    }}
    .chatbot-empty::before {{
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 5px;
      background: var(--mc-coral);
    }}
    .chatbot-empty__title {{
      margin: 0 0 0.35rem 0;
      padding-left: 0.55rem;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--mc-text);
      letter-spacing: -0.01em;
    }}
    .chatbot-empty__hint {{
      margin: 0 0 1rem 0;
      padding-left: 0.55rem;
      color: var(--mc-muted);
      font-size: 0.9rem;
    }}
    .chatbot-section-label {{
      margin: 0.85rem 0 0.45rem 0;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--mc-muted);
    }}
    .stApp:has(.chatbot-shell) div[data-testid="stChatInput"] {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      border-radius: 14px !important;
      box-shadow: var(--mc-shadow) !important;
      padding: 0.4rem 0.55rem 0.4rem 0.85rem !important;
    }}
    .stApp:has(.chatbot-shell) div[class*="st-key-chat_ex_"],
    .stApp:has(.chatbot-shell) div[class*="st-key-followup_"] {{
      margin-bottom: 0.35rem !important;
    }}
    .stApp:has(.chatbot-shell) div[class*="st-key-chat_ex_"] button,
    .stApp:has(.chatbot-shell) div[class*="st-key-followup_"] button {{
      justify-content: flex-start !important;
      text-align: left !important;
      min-height: 2.55rem !important;
      font-weight: 600 !important;
      border-radius: 14px !important;
    }}

    /* Soften only the page footer; do not hide MainMenu / hamburger */
    footer {{
      visibility: hidden;
      height: 0;
    }}

    /* Analyst login uses the shared customer split-login layout
       (.customer-login-marker + apply_customer_login_theme). */
    .stApp:has(.analyst-login-marker.customer-login-marker) [data-testid="stTextInput"] button {{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      min-height: auto !important;
      border-radius: 8px !important;
    }}

    /* Language dropdown — wide enough for "English" / "ไทย" */
    div[class*="st-key-_lang_selector"][data-testid="stSelectbox"],
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] {{
      width: 100% !important;
      min-width: 12.5rem !important;
      max-width: 16rem !important;
      margin-left: auto !important;
    }}
    div[class*="st-key-_lang_selector"][data-testid="stSelectbox"] > div,
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] > div {{
      width: 100% !important;
    }}
    div[class*="st-key-_lang_selector"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"][class*="st-key-_lang_selector"] div[data-baseweb="select"] > div {{
      background: var(--mc-surface) !important;
      border: 1px solid var(--mc-border) !important;
      box-shadow: var(--mc-shadow) !important;
      border-radius: 14px !important;
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

    /* Role chip in sidebar */
    .sidebar-role-chip {{
      display: inline-block;
      margin: 0.35rem 0 0.75rem;
      padding: 0.28rem 0.7rem;
      border-radius: 14px;
      background: var(--mc-peach);
      color: var(--mc-coral-deep);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}

    div[data-testid="stHorizontalBlock"]:has(.app-shell) {{
      align-items: center !important;
      gap: 0.65rem !important;
    }}
    div[data-testid="column"]:has([class*="st-key-_lang_selector"]) {{
      display: flex !important;
      align-items: center !important;
      justify-content: flex-end !important;
    }}

    @media (max-width: 768px) {{
      .app-shell__brand-name {{ font-size: 1.2rem; }}
      .stApp [data-testid="stMainBlockContainer"] {{
        max-width: 100% !important;
      }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_app_shell(title: str, subtitle: str | None = None, actions: list[str] | None = None):
    """Render the top brand shell. Visual chrome only."""
    actions = actions or []
    # Strip leading emoji if present so coral wordmark reads cleanly
    clean_title = title.replace("🏢 ", "").replace("🛒 ", "").strip()
    tagline = f'<p class="app-shell__brand-tagline">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="app-shell">
          <div class="app-shell__brand">
            <span class="app-shell__brand-name">{brand_wordmark_html(name=clean_title)}</span>
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
