import streamlit as st

from config import POWER_BI_EMBED_URL
from ui.i18n import t


def show_powerbi_dashboard():
    st.header(t("nav_power_bi"))
    st.caption(t("power_bi_caption"))

    embed_url = POWER_BI_EMBED_URL

    if not embed_url:
        st.error(t("power_bi_missing_url"))
        return

    custom_html = f"""
    <style>
        .pbi-wrapper {{
            width: 100%;
            max-width: 1920px;
            aspect-ratio: 16 / 9;
            margin: 1rem auto 0 auto;
            border-radius: 12px;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.12);
            overflow: hidden;
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 140, 158, 0.35);
        }}

        .pbi-iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
    </style>

    <div class="pbi-wrapper">
        <iframe
            class="pbi-iframe"
            title="E-commerce Fraud Analysis"
            src="{embed_url}"
            allowFullScreen="true">
        </iframe>
    </div>
    """

    st.markdown(custom_html, unsafe_allow_html=True)
