"""
config.py

Centralized configuration for the Smart Digital Library Management System.
All environment-specific values (DB credentials, paths, email settings)
live here so no other module hardcodes secrets or magic strings.

Values are read from environment variables with sane local-dev defaults.
In production, these should be set via a `.env` file (never committed)
or the OS environment directly.
"""

import os

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("LMS_DB_HOST", "localhost"),
    "port": os.getenv("LMS_DB_PORT", "5432"),
    "dbname": os.getenv("LMS_DB_NAME", "library_management_system"),
    "user": os.getenv("LMS_DB_USER", "postgres"),
    "password": os.getenv("LMS_DB_PASSWORD", ""),
}

# ---------------------------------------------------------------------------
# Application paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
QR_CODE_DIR = os.path.join(ASSETS_DIR, "qr_codes")
BOOK_COVER_DIR = os.path.join(ASSETS_DIR, "images")
SCHEMA_FILE = os.path.join(BASE_DIR, "database", "schema.sql")

# ---------------------------------------------------------------------------
# Fine rules (used later in Phase 10, defined centrally now so it's not
# scattered across modules once we build the Fine module)
# ---------------------------------------------------------------------------
FINE_RULES = [
    # (min_days, max_days_inclusive_or_None_for_infinite, rate_per_day)
    (1, 3, 5),
    (4, 7, 10),
    (8, 15, 20),
    (16, None, 50),
]

# ---------------------------------------------------------------------------
# Email configuration (Phase 12)
# Gmail's SMTP server, using an App Password (not the real account
# password) -- same "never hardcode secrets" principle as DB_CONFIG.
# ---------------------------------------------------------------------------
EMAIL_CONFIG = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,  # 587 = TLS (encrypted), the standard port for Gmail SMTP
    "sender_email": os.getenv("LMS_EMAIL_ADDRESS", ""),
    "sender_password": os.getenv("LMS_EMAIL_APP_PASSWORD", ""),
}