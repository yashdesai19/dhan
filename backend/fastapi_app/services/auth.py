"""Authentication service implementing core security workflows."""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.config import settings
from fastapi_app.core.mailer import send_password_reset
from fastapi_app.core.rate_limit import LOGIN_FAILURES_PER_EMAIL
from fastapi_app.core.security import (
    burn_password_check,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from fastapi_app.models.token import PasswordResetToken, RefreshToken
from fastapi_app.models.user import User
from fastapi_app.repositories.user import UserRepository
from fastapi_app.schemas.auth import UserRegisterRequest

security_log = logging.getLogger("fastapi_app.security")


def _account_ref(email: str) -> str:
    """Short, non-reversible reference for logs, so they can correlate without holding emails."""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:12]


class AuthService:
    """Service orchestrating registration, login, token refresh, and logout."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register_user(
        self,
        register_data: UserRegisterRequest,
    ) -> tuple[User, str, str]:
        """Register a new user account. Role is strictly assigned server-side as 'user'."""
        clean_email = register_data.email.strip().lower()

        # Check if email is already taken
        existing_user = await self.user_repo.get_by_email(clean_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )

        # Hash password securely
        pwd_hash = hash_password(register_data.password)

        # Server-enforced role: mobile client can never assign roles
        try:
            user = await self.user_repo.create(
                name=register_data.name,
                email=clean_email,
                password_hash=pwd_hash,
                role="user",
                status="active",
            )
        except IntegrityError:
            # Lost a race with a simultaneous registration of the same email
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            ) from None

        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email,
        )
        refresh_token, token_hash, expires_at = create_refresh_token(user_id=user.id)
        await self.user_repo.store_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        await self.session.commit()
        return user, access_token, refresh_token

    async def login_user(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        """Authenticate user by email and password."""
        clean_email = email.strip().lower()
        # Too many recent wrong passwords for this account: refuse before checking another
        LOGIN_FAILURES_PER_EMAIL.check(clean_email)
        user = await self.user_repo.get_by_email(clean_email)

        if user is None:
            burn_password_check(password)  # same cost as a wrong password: no email probing
        if user is None or not verify_password(password, user.password_hash):
            if settings.RATE_LIMIT_ENABLED:
                LOGIN_FAILURES_PER_EMAIL.record(clean_email)
            security_log.warning("Failed login for account ref %s", _account_ref(clean_email))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check account status
        if not user.is_active():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled. Contact support.",
            )

        # Update last login timestamp
        await self.user_repo.update_last_login(user)

        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email,
        )
        refresh_token, token_hash, expires_at = create_refresh_token(user_id=user.id)
        await self.user_repo.store_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        await self.session.commit()
        return user, access_token, refresh_token

    async def refresh_access_token(self, raw_refresh_token: str) -> tuple[str, str]:
        """Exchange a valid refresh token for a new access token and a new refresh token.

        Refresh tokens are single use. Presenting one that was already used or revoked means it
        has been copied, so every session of that user is ended.
        """
        try:
            payload = decode_token(raw_refresh_token)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token format or signature.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token.",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject.",
            )

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed user ID in token.",
            ) from None

        # Verify token in database (locked, so two refreshes of one token can't both succeed)
        token_digest = hash_token(raw_refresh_token)
        token_record = (
            await self.session.execute(
                select(RefreshToken)
                .where(RefreshToken.token_hash == token_digest)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if token_record is None or token_record.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or is invalid.",
            )
        if token_record.revoked:
            await self.user_repo.revoke_all_user_tokens(token_record.user_id)
            await self.session.commit()
            security_log.warning(
                "Revoked refresh token reused for user %s; all sessions ended", user_id
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or is invalid.",
            )

        now = datetime.now(UTC)
        if token_record.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired.",
            )

        # Retrieve user and verify status
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive or disabled.",
            )

        # Rotate: retire the presented token, issue a replacement
        token_record.revoked = True
        new_refresh_token, new_digest, expires_at = create_refresh_token(user_id=user.id)
        await self.user_repo.store_refresh_token(
            user_id=user.id, token_hash=new_digest, expires_at=expires_at
        )
        await self.session.commit()

        # Issue new access token using latest server-side role
        new_access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email,
        )
        return new_access_token, new_refresh_token

    async def update_profile(self, user: User, name: str) -> User:
        user.name = name
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def request_password_reset(self, email: str) -> None:
        """Issues a reset code if the account exists. The caller always gets the same answer,
        so this can't be used to find out which emails are registered."""
        user = await self.user_repo.get_by_email(email)
        if user is None or not user.is_active():
            return
        raw = secrets.token_urlsafe(24)
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES),
            )
        )
        await self.session.commit()
        send_password_reset(user.email, raw)

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        """Sets a new password with a valid code, then ends every existing session."""
        record = (
            await self.session.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.token_hash == hash_token(raw_token))
                .with_for_update()
            )
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if record is None or record.used_at is not None or record.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset code is invalid or has expired.",
            )
        user = await self.user_repo.get_by_id(record.user_id)
        if user is None or not user.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset code is invalid or has expired.",
            )
        user.password_hash = hash_password(new_password)
        record.used_at = now
        await self.user_repo.revoke_all_user_tokens(user.id)
        await self.session.commit()
        security_log.warning("Password reset completed for user %s", user.id)

    async def logout_user(
        self,
        current_user: User,
        raw_refresh_token: str | None = None,
    ) -> None:
        """Revoke refresh token(s) upon user logout."""
        if raw_refresh_token:
            token_digest = hash_token(raw_refresh_token)
            await self.user_repo.revoke_refresh_token(token_digest, user_id=current_user.id)
        else:
            # Revoke all tokens for user if no specific refresh token provided
            await self.user_repo.revoke_all_user_tokens(current_user.id)

        await self.session.commit()
