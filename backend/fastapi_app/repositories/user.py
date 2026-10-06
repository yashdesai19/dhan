"""User and RefreshToken repository handling asynchronous database queries."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.models.token import RefreshToken
from fastapi_app.models.user import User


class UserRepository:
    """Repository handling User and RefreshToken operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key UUID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by case-insensitive email address."""
        clean_email = email.strip().lower()
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == clean_email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "user",
        status: str = "active",
    ) -> User:
        """Create and persist a new user."""
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            status=status,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user: User) -> None:
        """Update last login timestamp to now."""
        user.last_login_at = datetime.now(UTC)
        self.session.add(user)
        await self.session.flush()

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Persist refresh token metadata for validity checking."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        """Retrieve refresh token record by token hash."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str, user_id: uuid.UUID) -> bool:
        """Mark one of this user's refresh tokens as revoked (others' tokens are untouched)."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.user_id == user_id)
            .values(revoked=True)
        )
        rowcount = getattr(result, "rowcount", 0)
        return (rowcount or 0) > 0

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user (e.g., security reset or full logout)."""
        await self.session.execute(
            update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True)
        )
