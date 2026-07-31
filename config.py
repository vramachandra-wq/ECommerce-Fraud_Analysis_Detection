"""Environment configuration for the fraud detection app."""
import os
from dotenv import load_dotenv

# Adding override=True ensures .env variables take precedence 
# over existing system environment variables.
load_dotenv(override=True)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "fraud_detection"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
    # Order timestamps are written as UTC wall-clock (naive). Keep the DB session
    # on UTC so NOW() / CURRENT_DATE match those values.
    "options": "-c timezone=UTC",
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
# TLS verify for Groq HTTP. Set GROQ_SSL_VERIFY=false only behind SSL-inspecting proxies.
_groq_ssl = os.environ.get("GROQ_SSL_VERIFY", "true").strip().lower()
GROQ_SSL_VERIFY = _groq_ssl not in {"0", "false", "no", "off"}

_GROQ_KEY_PLACEHOLDERS = {
    "",
    "your_groq_api_key_here",
    "changeme",
    "replace_me",
}


def is_groq_api_key_configured() -> bool:
    """True when a non-placeholder Groq API key is present in the environment."""
    return GROQ_API_KEY.lower() not in _GROQ_KEY_PLACEHOLDERS

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "10"))
POWER_BI_EMBED_URL = os.environ.get("POWER_BI_EMBED_URL", "")

_cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").strip()
if _cors_origins == "":
    CORS_ALLOW_ORIGINS = ["*"]
else:
    CORS_ALLOW_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

# Analyst portal session tokens (also signs OIDC state for SSO).
PORTAL_SECRET = _get_env_str("PORTAL_SECRET", "metro-cart-dev-portal-secret")
PORTAL_TOKEN_TTL = int(os.environ.get("PORTAL_TOKEN_TTL", "86400"))

# Optional Keycloak OIDC SSO for the analyst portal (local password login remains).
_keycloak_flag = os.environ.get("KEYCLOAK_ENABLED", "true").strip().lower()
KEYCLOAK_ENABLED = _keycloak_flag in {"1", "true", "yes", "on"}
KEYCLOAK_URL = _get_env_str("KEYCLOAK_URL", "http://127.0.0.1:8080")
KEYCLOAK_REALM = _get_env_str("KEYCLOAK_REALM", "metro-cart")
KEYCLOAK_CLIENT_ID = _get_env_str("KEYCLOAK_CLIENT_ID", "analyst-portal")
KEYCLOAK_CLIENT_SECRET = _get_env_str("KEYCLOAK_CLIENT_SECRET", "metro-cart-sso-secret")
KEYCLOAK_ADMIN = _get_env_str("KEYCLOAK_ADMIN", "")
KEYCLOAK_ADMIN_PASSWORD = _get_env_str("KEYCLOAK_ADMIN_PASSWORD", "")
KEYCLOAK_REDIRECT_URI = _get_env_str(
    "KEYCLOAK_REDIRECT_URI",
    "http://127.0.0.1:8000/auth/sso/callback",
)
SSO_DEFAULT_RETURN_TO = _get_env_str(
    "SSO_DEFAULT_RETURN_TO",
    f"{API_BASE_URL.rstrip('/')}/portal/",
)