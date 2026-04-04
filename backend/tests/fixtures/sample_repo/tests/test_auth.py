"""Tests for authentication module."""

from auth.token_handler import TokenManager, hash_password, verify_password


def test_create_token():
    tm = TokenManager(secret_key="test-secret")
    token = tm.create_token("user1")
    assert token is not None
    assert len(token) > 0


def test_validate_token():
    tm = TokenManager(secret_key="test-secret")
    token = tm.create_token("user1")
    info = tm.validate_token(token)
    assert info is not None
    assert info["user_id"] == "user1"


def test_rotate_token():
    tm = TokenManager(secret_key="test-secret")
    old_token = tm.create_token("user1")
    new_token = tm.rotate_token(old_token)
    assert new_token is not None
    assert new_token != old_token
    assert tm.validate_token(old_token) is None
    assert tm.validate_token(new_token) is not None


def test_revoke_token():
    tm = TokenManager(secret_key="test-secret")
    token = tm.create_token("user1")
    assert tm.revoke_token(token) is True
    assert tm.validate_token(token) is None


def test_hash_password():
    hashed = hash_password("secret123", "salt")
    assert verify_password("secret123", hashed, "salt")
    assert not verify_password("wrong", hashed, "salt")
