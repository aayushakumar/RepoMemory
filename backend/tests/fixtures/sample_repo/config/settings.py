"""Application configuration settings."""

import os

# Server settings
HOST = os.environ.get("APP_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT", "8080"))
DEBUG = os.environ.get("APP_DEBUG", "false").lower() == "true"

# Auth settings
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
TOKEN_ROTATION_ENABLED = os.environ.get("TOKEN_ROTATION", "true").lower() == "true"

# Database
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT", "60"))
