"""Environment configuration for the fraud detection app."""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "fraud_detection"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}


def _get_env_str(key: str, default: str = "") -> str:
    value = os.environ.get(key, default)
    if isinstance(value, str):
        return value.strip().strip('"').strip("'")
    return default


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_INTENT_MODEL = _get_env_str("GROQ_INTENT_MODEL", "openai/gpt-oss-20b")
GROQ_SQL_MODEL = _get_env_str("GROQ_SQL_MODEL", "openai/gpt-oss-120b")
GROQ_REPAIR_MODEL = _get_env_str("GROQ_REPAIR_MODEL", "openai/gpt-oss-120b")
GROQ_SUMMARY_MODEL = _get_env_str("GROQ_SUMMARY_MODEL", "openai/gpt-oss-120b")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "10"))
POWER_BI_EMBED_URL = os.environ.get("POWER_BI_EMBED_URL", "")

_cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").strip()
if _cors_origins == "":
    CORS_ALLOW_ORIGINS = ["*"]
else:
    CORS_ALLOW_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]
