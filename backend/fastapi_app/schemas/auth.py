"""Authentication and User Pydantic v2 schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from fastapi_app.core.security import BCRYPT_MAX_BYTES


class UserRegisterRequest(BaseModel):
    """Schema for POST /auth/register. Role is never accepted from the client."""

    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Secure password (at most 72 bytes)"
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes")
        return v


class UserLoginRequest(BaseModel):
    """Schema for POST /auth/login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, max_length=1024, description="Account password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TokenRefreshRequest(BaseModel):
    """Schema for POST /auth/refresh."""

    refresh_token: str = Field(
        ..., min_length=10, max_length=2048, description="Valid refresh token"
    )


class TokenLogoutRequest(BaseModel):
    """Schema for POST /auth/logout."""

    refresh_token: str | None = Field(
        default=None, max_length=2048, description="Optional refresh token to revoke"
    )


class ProfileUpdate(BaseModel):
    """Fields a user may change about themselves (email and role are not among them)."""

    name: str = Field(..., min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes")
        return v


class UserPublic(BaseModel):
    """Public user representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    """Full authentication response containing tokens and public user details."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class TokenRefreshResponse(BaseModel):
    """A new access token and the refresh token that replaces the one just used."""

    access_token: str
    refresh_token: str = Field(
        ..., description="Use this next time; the refresh token you sent is now revoked"
    )
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Standard message response."""

    message: str
