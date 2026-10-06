"""Security utilities: password hashing and JWT token management."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from fastapi_app.core.config import settings

# bcrypt only reads the first 72 bytes of a password (and bcrypt>=5 refuses longer input)
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash plaintext password securely using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


# Checked when an email has no account, so a miss costs the same time as a wrong password and
# response timing doesn't reveal which emails are registered.
_TIMING_DUMMY_HASH = bcrypt.hashpw(b"dhan-timing-equaliser", bcrypt.gensalt(rounds=12)).decode()


def burn_password_check(plain_password: str) -> None:
    verify_password(plain_password, _TIMING_DUMMY_HASH)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def hash_token(raw_token: str) -> str:
    """Create a SHA256 digest of a token for safe indexing and database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: uuid.UUID | str,
    role: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate signed JWT access token containing user identity and role."""
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email.strip().lower(),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: uuid.UUID | str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    """Generate signed JWT refresh token. Returns (raw_token, token_hash, expires_at)."""
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    raw_jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": raw_jti,
    }
    raw_token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    token_digest = hash_token(raw_token)
    return raw_token, token_digest, expire


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "type"]},
    )
