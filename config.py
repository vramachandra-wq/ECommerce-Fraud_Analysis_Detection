"""Environment configuration for the fraud detection app."""
import logging
import os
import warnings

from dotenv import load_dotenv

# Adding override=True ensures .env variables take precedence
# over existing system environment variables.
load_dotenv(override=True)

_logger = logging.getLogger(__name__)

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


def _env_flag(key: str, default: str = "false") -> bool:
    return os.environ.get(key, default).strip().lower() in {"1", "true", "yes", "on"}


# development (default) keeps local/demo defaults working.
# production / staging enforce stronger secrets and Secure cookies.
APP_ENV = _get_env_str("APP_ENV", "development").lower() or "development"
IS_PRODUCTION = APP_ENV in {"production", "prod", "staging"}

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
# Prefer the faster 20B model by default. Override to gpt-oss-120b in .env for max quality.
GROQ_INTENT_MODEL = _get_env_str("GROQ_INTENT_MODEL", "openai/gpt-oss-120b")
GROQ_SQL_MODEL = _get_env_str("GROQ_SQL_MODEL", "openai/gpt-oss-120b")
GROQ_REPAIR_MODEL = _get_env_str("GROQ_REPAIR_MODEL", "openai/gpt-oss-120b")
GROQ_SUMMARY_MODEL = _get_env_str("GROQ_SUMMARY_MODEL", "openai/gpt-oss-120b")
# TLS verify for Groq HTTP. Production defaults to true; local/dev defaults to false
# for SSL-inspecting corporate proxies (Zscaler etc.). Override with GROQ_SSL_VERIFY.
_groq_ssl_default = "true" if IS_PRODUCTION else "false"
_groq_ssl = os.environ.get("GROQ_SSL_VERIFY", _groq_ssl_default).strip().lower()
GROQ_SSL_VERIFY = _groq_ssl in {"1", "true", "yes", "on"}

_GROQ_KEY_PLACEHOLDERS = {
    "",
    "your_groq_api_key_here",
    "changeme",
    "replace_me",
}

_WEAK_SECRETS = {
    "",
    "changeme",
    "replace_me",
    "replace_with_a_long_random_secret",
    "replace_with_a_client_secret",
    "metro-cart-dev-portal-secret",
    "metro-cart-sso-secret",
    "ci-test-secret",
    "deploy-placeholder-change-in-target-env",
}


def is_groq_api_key_configured() -> bool:
    """True when a non-placeholder Groq API key is present in the environment."""
    return GROQ_API_KEY.lower() not in _GROQ_KEY_PLACEHOLDERS


def _is_weak_secret(value: str, *, min_length: int = 32) -> bool:
    cleaned = (value or "").strip()
    if cleaned.lower() in _WEAK_SECRETS:
        return True
    return len(cleaned) < min_length


API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "10"))
POWER_BI_EMBED_URL = os.environ.get("POWER_BI_EMBED_URL", "")

_cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").strip()
if _cors_origins == "":
    CORS_ALLOW_ORIGINS = ["*"]
else:
    CORS_ALLOW_ORIGINS = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

# Analyst portal session tokens (also signs OIDC state for SSO).
# Dev default kept for local demos; production refuses weak values at startup.
PORTAL_SECRET = _get_env_str("PORTAL_SECRET", "metro-cart-dev-portal-secret")
PORTAL_TOKEN_TTL = int(os.environ.get("PORTAL_TOKEN_TTL", "86400"))

# Cookie Secure flag: on in production by default; off for local HTTP.
# Set COOKIE_SECURE=true behind HTTPS even in non-production if needed.
_cookie_secure_default = "true" if IS_PRODUCTION else "false"
COOKIE_SECURE = _env_flag("COOKIE_SECURE", _cookie_secure_default)

# Login brute-force protection (in-process; resets on API restart).
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))
LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "900"))

# When true (default in production), schema ensure failures abort startup.
_schema_strict_default = "true" if IS_PRODUCTION else "false"
SCHEMA_STRICT = _env_flag("SCHEMA_STRICT", _schema_strict_default)

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

# Microsoft Graph email alerts (application Mail.Send).
_email_alerts_flag = os.environ.get("EMAIL_ALERTS_ENABLED", "false").strip().lower()
EMAIL_ALERTS_ENABLED = _email_alerts_flag in {"1", "true", "yes", "on"}
# Prefer AZURE_* names; fall back to the IT-issued Application_ID / Tenent_ID keys.
AZURE_CLIENT_ID = _get_env_str("AZURE_CLIENT_ID") or _get_env_str("Application_ID")
AZURE_TENANT_ID = (
    _get_env_str("AZURE_TENANT_ID")
    or _get_env_str("Tenant_ID")
    or _get_env_str("Tenent_ID")
)
AZURE_CLIENT_SECRET = _get_env_str("AZURE_CLIENT_SECRET") or _get_env_str("Secret_Value")
GRAPH_SENDER_EMAIL = _get_env_str("GRAPH_SENDER_EMAIL", "sudayasurriyan@aziro.com")
GRAPH_SENDER_NAME = _get_env_str("GRAPH_SENDER_NAME", "Fraud Portal Alerts")
# Comma-separated analyst roles that receive backlog digests.
_backlog_roles = _get_env_str("BACKLOG_ALERT_ROLES", "Admin")
BACKLOG_ALERT_ROLES = tuple(
    role.strip() for role in _backlog_roles.split(",") if role.strip()
)
BACKLOG_ALERT_INTERVAL_MINUTES = int(os.environ.get("BACKLOG_ALERT_INTERVAL_MINUTES", "60"))


def is_graph_mail_configured() -> bool:
    """True when Graph app credentials and sender mailbox are present."""
    return bool(AZURE_CLIENT_ID and AZURE_TENANT_ID and AZURE_CLIENT_SECRET and GRAPH_SENDER_EMAIL)
