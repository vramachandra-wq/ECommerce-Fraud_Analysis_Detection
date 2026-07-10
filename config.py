"""Environment configuration for the fraud detection app."""
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "fraud_detection"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

# R001 hold window, in minutes (kept configurable rather than hardcoded in the engine)
R001_HOLD_MINUTES = 180

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_SQL_MODEL = os.getenv("GROQ_SQL_MODEL", "openai/gpt-oss-120b")
GROQ_REPAIR_MODEL = os.getenv("GROQ_REPAIR_MODEL", "openai/gpt-oss-120b")
GROQ_SUMMARY_MODEL = os.getenv("GROQ_SUMMARY_MODEL", "openai/gpt-oss-120b")

# App configuration
MAX_HISTORY = 8
MAX_STORED_MESSAGES = 100
MARKDOWN_PREVIEW_ROWS = 15
