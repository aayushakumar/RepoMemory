"""API route handlers."""

from dataclasses import dataclass


@dataclass
class Response:
    status: int
    body: dict


def handle_login(username: str, password: str) -> Response:
    """Handle user login request."""
    if not username or not password:
        return Response(status=400, body={"error": "Missing credentials"})
    # In a real app, verify against database
    return Response(status=200, body={"message": "Login successful", "username": username})


def handle_register(username: str, email: str, password: str) -> Response:
    """Handle user registration."""
    if not all([username, email, password]):
        return Response(status=400, body={"error": "Missing fields"})
    return Response(status=201, body={"message": "User created", "username": username})


def handle_profile(user_id: str) -> Response:
    """Get user profile."""
    return Response(status=200, body={"user_id": user_id, "profile": "data"})


def handle_logout(token: str) -> Response:
    """Handle logout request."""
    return Response(status=200, body={"message": "Logged out"})
