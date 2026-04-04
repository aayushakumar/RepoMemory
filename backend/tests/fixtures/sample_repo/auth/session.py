"""User model and session management."""


class User:
    """Represents a user in the system."""

    def __init__(self, user_id: str, username: str, email: str):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.is_active = True

    def deactivate(self):
        self.is_active = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
        }


class SessionManager:
    """Manages user sessions."""

    def __init__(self):
        self._sessions: dict[str, User] = {}

    def create_session(self, token: str, user: User) -> None:
        self._sessions[token] = user

    def get_session(self, token: str) -> User | None:
        return self._sessions.get(token)

    def invalidate_session(self, token: str) -> bool:
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def get_active_sessions_count(self) -> int:
        return len(self._sessions)
