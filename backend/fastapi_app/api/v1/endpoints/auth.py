"""Authentication endpoints for DHAN."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_admin, require_current_user
from fastapi_app.core.rate_limit import limit_login, limit_refresh, limit_register, limit_reset
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    ProfileUpdate,
    ResetPasswordRequest,
    TokenLogoutRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserPublic,
    UserRegisterRequest,
)
from fastapi_app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    dependencies=[Depends(limit_register)],
)
async def register(
    data: UserRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new DHAN user.

    The role is unconditionally set to 'user' server-side.
    Client-supplied roles are completely discarded.
    """
    auth_service = AuthService(session)
    user, access_token, refresh_token = await auth_service.register_user(data)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue tokens",
    dependencies=[Depends(limit_login)],
)
async def login(
    data: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password to receive access & refresh tokens."""
    auth_service = AuthService(session)
    user, access_token, refresh_token = await auth_service.login_user(
        email=data.email,
        password=data.password,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    dependencies=[Depends(limit_refresh)],
)
async def refresh_token(
    data: TokenRefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenRefreshResponse:
    """Exchange a refresh token for a new access token and a replacement refresh token."""
    auth_service = AuthService(session)
    new_access_token, new_refresh_token = await auth_service.refresh_access_token(
        data.refresh_token
    )
    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: Annotated[User, Depends(require_current_user)],
) -> UserPublic:
    """Retrieve profile and server-enforced role of currently authenticated user."""
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic, summary="Update your own profile")
async def update_me(
    data: ProfileUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserPublic:
    """Change your display name."""
    user = await AuthService(session).update_profile(current_user, data.name)
    return UserPublic.model_validate(user)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_reset)],
)
async def forgot_password(
    data: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Send a reset code if the account exists. Same answer either way."""
    await AuthService(session).request_password_reset(data.email)
    return MessageResponse(message="If that email has an account, a reset code is on its way.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(limit_reset)],
)
async def reset_password(
    data: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Set a new password with a reset code; signs out every existing session."""
    await AuthService(session).reset_password(data.token, data.new_password)
    return MessageResponse(message="Your password has been changed. Please log in.")


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out and revoke refresh token",
)
async def logout(
    current_user: Annotated[User, Depends(require_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    data: TokenLogoutRequest | None = None,
) -> MessageResponse:
    """Revoke refresh token session for the authenticated user."""
    auth_service = AuthService(session)
    refresh_token = data.refresh_token if data else None
    await auth_service.logout_user(current_user, raw_refresh_token=refresh_token)
    return MessageResponse(message="Successfully logged out.")


@router.get(
    "/admin-only",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin-only authorization checkpoint",
)
async def admin_only_endpoint(
    current_admin: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    """Endpoint accessible ONLY to authenticated users with role='admin'.

    Normal users attempting access are rejected with HTTP 403 Forbidden.
    """
    return MessageResponse(message=f"Admin privileges verified for {current_admin.email}.")
