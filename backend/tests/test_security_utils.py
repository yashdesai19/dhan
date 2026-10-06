"""Test cryptographic functions, password hashing, and JWT tokens."""

import uuid
from datetime import timedelta

import jwt
import pytest

from fastapi_app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    """Requirement 6: Verify password hashing is secure, non-plaintext, and verifiable."""
    plain = "SuperSecretPassword123!"
    hashed = hash_password(plain)

    # Password must never be stored as plaintext
    assert hashed != plain
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt format

    # Verify correct password succeeds
    assert verify_password(plain, hashed) is True

    # Verify incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False

    # Verify different salts produce distinct hashes for same plaintext
    hashed2 = hash_password(plain)
    assert hashed != hashed2
    assert verify_password(plain, hashed2) is True


def test_jwt_generation_and_validation() -> None:
    """Requirements 7 & 8: Verify JWT generation, structure, and validation."""
    user_id = uuid.uuid4()
    email = "investor@dhan.com"
    role = "user"

    token = create_access_token(user_id=user_id, role=role, email=email)
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_tampering_and_invalid_token() -> None:
    """Requirement 10: Verify tampered or invalid token fails validation."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="user", email="test@dhan.com")

    # Tampered token signature
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.tampered_signature"

    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)

    # Completely invalid string
    with pytest.raises(jwt.PyJWTError):
        decode_token("not-a-token")


def test_jwt_expiration() -> None:
    """Requirement 11: Verify expired tokens are rejected."""
    user_id = uuid.uuid4()
    # Generate token expired 5 seconds ago
    expired_token = create_access_token(
        user_id=user_id,
        role="user",
        email="test@dhan.com",
        expires_delta=timedelta(seconds=-5),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)


def test_refresh_token_generation_and_hash() -> None:
    """Requirement 12: Verify refresh token generation, hashing, and payload."""
    user_id = uuid.uuid4()
    raw_token, token_hash, expires_at = create_refresh_token(user_id=user_id)

    assert isinstance(raw_token, str)
    assert isinstance(token_hash, str)
    assert token_hash == hash_token(raw_token)

    payload = decode_token(raw_token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "jti" in payload
