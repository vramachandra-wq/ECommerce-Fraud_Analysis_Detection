import streamlit as st
from groq import Groq
from config import GROQ_API_KEY

st.write("API Key:", GROQ_API_KEY)


_client = None


def get_groq_client():
    global _client

    if _client is None:
        if not GROQ_API_KEY:
            return None

        _client = Groq(api_key=GROQ_API_KEY)

    return _client

