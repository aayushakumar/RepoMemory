"""Tests for API routes."""

from routes.api import handle_login, handle_profile, handle_register


def test_login_success():
    response = handle_login("admin", "password")
    assert response.status == 200


def test_login_missing_credentials():
    response = handle_login("", "password")
    assert response.status == 400


def test_register():
    response = handle_register("newuser", "new@example.com", "pass123")
    assert response.status == 201


def test_profile():
    response = handle_profile("user-123")
    assert response.status == 200
