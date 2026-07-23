import streamlit as st
from config import POWER_BI_EMBED_URL
from ui.i18n import t


def show_powerbi_dashboard():
    st.markdown(
        f'<p class="page-heading">{t("nav_power_bi")}</p>',
        unsafe_allow_html=True,
    )

    embed_url = POWER_BI_EMBED_URL

    if not embed_url:
        st.error(t("err_power_bi_missing"))
        return

    custom_html = f"""
    <style>
        .pbi-wrapper {{
            width: 100%;
            max-width: 1920px;
            aspect-ratio: 16 / 9;
            margin: 0.35rem auto 0 auto;
            border-radius: var(--mc-radius, 18px);
            box-shadow: var(--mc-shadow, 0 18px 48px rgba(30, 30, 30, 0.08));
            overflow: hidden;
            background-color: var(--mc-surface, #ffffff);
            border: 1px solid var(--mc-border, rgba(30, 30, 30, 0.08));
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
            title="{t("nav_power_bi")}"
            src="{embed_url}"
            allowFullScreen="true">
        </iframe>
    </div>
    """

    st.markdown(custom_html, unsafe_allow_html=True)
