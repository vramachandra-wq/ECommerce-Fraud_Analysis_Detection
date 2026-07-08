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
