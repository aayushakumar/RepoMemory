"""Authentication module for the sample app."""

import hashlib
import secrets
from datetime import datetime, timedelta


class TokenManager:
    """Manages JWT-like tokens for user sessions."""

    def __init__(self, secret_key: str, expiry_hours: int = 24):
        self.secret_key = secret_key
        self.expiry_hours = expiry_hours
        self._active_tokens: dict[str, dict] = {}

    def create_token(self, user_id: str) -> str:
        """Create a new authentication token for a user."""
        token = secrets.token_urlsafe(32)
        self._active_tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=self.expiry_hours),
        }
        return token

    def validate_token(self, token: str) -> dict | None:
        """Validate a token and return user info if valid."""
        info = self._active_tokens.get(token)
        if not info:
            return None
        if datetime.utcnow() > info["expires_at"]:
            del self._active_tokens[token]
            return None
        return info

    def rotate_token(self, old_token: str) -> str | None:
        """Rotate an existing token — invalidate old, issue new."""
        info = self.validate_token(old_token)
        if not info:
            return None
        del self._active_tokens[old_token]
        return self.create_token(info["user_id"])

    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        return False


def hash_password(password: str, salt: str = "") -> str:
    """Hash a password with optional salt."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str, salt: str = "") -> bool:
    """Verify a password against its hash."""
    return hash_password(password, salt) == hashed
