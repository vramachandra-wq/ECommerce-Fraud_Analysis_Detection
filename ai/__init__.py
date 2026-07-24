"""AI package for Metro Cart analytics chatbot."""

from .groq_client import get_groq_client

__all__ = [
    "get_groq_client",
]


def __getattr__(name: str):
    # Lazy import avoids loading Streamlit chatbot UI unless needed.
    if name == "render_chatbot_tab":
        from .chatbot import render_chatbot_tab

        return render_chatbot_tab
    raise AttributeError(name)
