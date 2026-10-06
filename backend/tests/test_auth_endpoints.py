"""Comprehensive test suite for DHAN authentication, authorization, and roles."""

import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from fastapi_app.core.security import create_access_token, hash_password
from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.user import User


@pytest.mark.asyncio
async def test_01_register_user_success(async_client: httpx.AsyncClient) -> None:
    """1. Test successful user registration."""
    unique_email = f"user_{uuid.uuid4().hex[:8]}@dhan.com"
    payload = {
        "name": "Arjun Sharma",
        "email": unique_email,
        "password": "StrongPassword123!",
    }
    response = await async_client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == unique_email
    assert data["user"]["name"] == "Arjun Sharma"
    # Role must be assigned server-side as 'user'
    assert data["user"]["role"] == "user"
    assert data["user"]["status"] == "active"


@pytest.mark.asyncio
async def test_02_register_client_cannot_escalate_role(async_client: httpx.AsyncClient) -> None:
    """Security check: Client attempting to send role='admin' in registration is ignored."""
    unique_email = f"hacker_{uuid.uuid4().hex[:8]}@dhan.com"
    payload = {
        "name": "Attacker",
        "email": unique_email,
        "password": "Password12345!",
        "role": "admin",  # Attacker attempts to become admin
    }
    response = await async_client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    # Server strictly overrides/ignores and forces 'user'
    assert data["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_03_duplicate_email(async_client: httpx.AsyncClient) -> None:
    """2. Test duplicate email registration fails with HTTP 409 Conflict."""
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@dhan.com"
    payload = {
        "name": "Original User",
        "email": unique_email,
        "password": "Password123!",
    }
    resp1 = await async_client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    # Attempt second registration with same email
    resp2 = await async_client.post("/auth/register", json=payload)
    assert resp2.status_code == 409
    assert "already registered" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_04_invalid_password_validation(async_client: httpx.AsyncClient) -> None:
    """3. Test password minimum length validation (< 8 characters)."""
    payload = {
        "name": "Short Password",
        "email": f"short_{uuid.uuid4().hex[:8]}@dhan.com",
        "password": "short",  # Less than 8 characters
    }
    response = await async_client.post("/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_05_login_success(async_client: httpx.AsyncClient) -> None:
    """4. Test successful login returning JWT access and refresh tokens."""
    email = f"login_ok_{uuid.uuid4().hex[:8]}@dhan.com"
    password = "CorrectPassword123!"

    # Register first
    await async_client.post(
        "/auth/register",
        json={"name": "Login User", "email": email, "password": password},
    )

    # Login
    response = await async_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_06_login_failure_wrong_password(async_client: httpx.AsyncClient) -> None:
    """5. Test login failure with wrong password returns HTTP 401."""
    email = f"fail_{uuid.uuid4().hex[:8]}@dhan.com"
    password = "CorrectPassword123!"

    await async_client.post(
        "/auth/register",
        json={"name": "Fail User", "email": email, "password": password},
    )

    response = await async_client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_07_login_failure_nonexistent_email(async_client: httpx.AsyncClient) -> None:
    """5b. Test login failure with non-existent email returns HTTP 401."""
    response = await async_client.post(
        "/auth/login",
        json={"email": "nobody_exists@dhan.com", "password": "Password123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_08_get_current_user_me(async_client: httpx.AsyncClient) -> None:
    """9. Test GET /auth/me returns the authenticated user's profile."""
    email = f"me_{uuid.uuid4().hex[:8]}@dhan.com"
    reg = await async_client.post(
        "/auth/register",
        json={"name": "Priya Patel", "email": email, "password": "Password123!"},
    )
    access_token = reg.json()["access_token"]

    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["name"] == "Priya Patel"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_09_invalid_token_rejected(async_client: httpx.AsyncClient) -> None:
    """10. Test invalid token on protected endpoint returns HTTP 401."""
    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_10_expired_token_rejected(async_client: httpx.AsyncClient) -> None:
    """11. Test expired access token returns HTTP 401."""
    user_id = uuid.uuid4()
    expired_token = create_access_token(
        user_id=user_id,
        role="user",
        email="test@dhan.com",
        expires_delta=timedelta(seconds=-10),
    )
    response = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_11_refresh_token_lifecycle(async_client: httpx.AsyncClient) -> None:
    """12. Test POST /auth/refresh generates a fresh access token."""
    email = f"refresh_{uuid.uuid4().hex[:8]}@dhan.com"
    reg = await async_client.post(
        "/auth/register",
        json={"name": "Refresh User", "email": email, "password": "Password123!"},
    )
    refresh_token = reg.json()["refresh_token"]

    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify newly issued token works on /auth/me
    new_token = data["access_token"]
    me_resp = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


@pytest.mark.asyncio
async def test_12_logout_revokes_refresh_token(async_client: httpx.AsyncClient) -> None:
    """13. Test POST /auth/logout revokes refresh token so it cannot be reused."""
    email = f"logout_{uuid.uuid4().hex[:8]}@dhan.com"
    reg = await async_client.post(
        "/auth/register",
        json={"name": "Logout User", "email": email, "password": "Password123!"},
    )
    access_token = reg.json()["access_token"]
    refresh_token = reg.json()["refresh_token"]

    # Logout
    logout_resp = await async_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200
    assert "logged out" in logout_resp.json()["message"].lower()

    # Attempting to use the revoked refresh token must now fail
    ref_fail = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_fail.status_code == 401
    assert "revoked" in ref_fail.json()["detail"].lower()


@pytest.mark.asyncio
async def test_13_normal_user_vs_admin_authorization(async_client: httpx.AsyncClient) -> None:
    """14 & 15. Verify role-based authorization:

    - Normal user -> admin endpoint = 403 Forbidden
    - Admin user -> admin endpoint = allowed (200 OK)
    """
    # 1. Register a normal user
    normal_email = f"normal_{uuid.uuid4().hex[:8]}@dhan.com"
    reg_normal = await async_client.post(
        "/auth/register",
        json={"name": "Regular User", "email": normal_email, "password": "Password123!"},
    )
    normal_token = reg_normal.json()["access_token"]

    # Normal user accesses /auth/me -> allowed
    me_resp = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {normal_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "user"

    # Normal user attempts to access /auth/admin-only -> MUST BE 403 Forbidden
    forbidden_resp = await async_client.get(
        "/auth/admin-only",
        headers={"Authorization": f"Bearer {normal_token}"},
    )
    assert forbidden_resp.status_code == 403
    assert "administrator privileges required" in forbidden_resp.json()["detail"].lower()

    # 2. Create an admin user server-side in the database
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@dhan.com"
    admin_password = "AdminSecurePassword123!"
    async with AsyncSessionLocal() as session:
        admin_user = User(
            name="System Administrator",
            email=admin_email,
            password_hash=hash_password(admin_password),
            role="admin",  # Server-side designated admin
            status="active",
        )
        session.add(admin_user)
        await session.commit()

    # Admin logs in
    admin_login = await async_client.post(
        "/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    assert admin_login.json()["user"]["role"] == "admin"

    # Admin accesses /auth/admin-only -> MUST BE ALLOWED (200 OK)
    allowed_resp = await async_client.get(
        "/auth/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed_resp.status_code == 200
    assert "admin privileges verified" in allowed_resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_14_disabled_user_cannot_login_or_access(async_client: httpx.AsyncClient) -> None:
    """16. Test that disabled user cannot log in or access protected endpoints."""
    disabled_email = f"disabled_{uuid.uuid4().hex[:8]}@dhan.com"
    pwd = "Password123!"

    async with AsyncSessionLocal() as session:
        user = User(
            name="Disabled User",
            email=disabled_email,
            password_hash=hash_password(pwd),
            role="user",
            status="disabled",  # Explicitly disabled
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    # 1. Attempt login with valid credentials -> rejected
    login_resp = await async_client.post(
        "/auth/login",
        json={"email": disabled_email, "password": pwd},
    )
    assert login_resp.status_code == 403
    assert "disabled" in login_resp.json()["detail"].lower()

    # 2. Attempt token access -> rejected
    test_token = create_access_token(user_id=user_id, role="user", email=disabled_email)
    me_resp = await async_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {test_token}"},
    )
    assert me_resp.status_code == 403
    assert "disabled" in me_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_15_case_insensitive_email_handling(async_client: httpx.AsyncClient) -> None:
    """17. Test case-insensitive email registration, duplicate detection, and login."""
    mixed_email = f"Karan.Verma_{uuid.uuid4().hex[:6]}@dhan.com"
    password = "Password123!"

    # Register with mixed case
    reg = await async_client.post(
        "/auth/register",
        json={"name": "Karan Verma", "email": mixed_email, "password": password},
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["email"] == mixed_email.strip().lower()

    # Duplicate check with different case must be detected as duplicate
    dup_resp = await async_client.post(
        "/auth/register",
        json={"name": "Karan Verma Clone", "email": mixed_email.lower(), "password": password},
    )
    assert dup_resp.status_code == 409

    # Login with all uppercase
    login_upper = await async_client.post(
        "/auth/login",
        json={"email": mixed_email.upper(), "password": password},
    )
    assert login_upper.status_code == 200

    # Login with all lowercase
    login_lower = await async_client.post(
        "/auth/login",
        json={"email": mixed_email.lower(), "password": password},
    )
    assert login_lower.status_code == 200


@pytest.mark.asyncio
async def test_16_database_persistence(async_client: httpx.AsyncClient) -> None:
    """18. Verify user persists in PostgreSQL across distinct database sessions."""
    email = f"persist_{uuid.uuid4().hex[:8]}@dhan.com"
    await async_client.post(
        "/auth/register",
        json={"name": "Persistent User", "email": email, "password": "Password123!"},
    )

    # Open completely new independent session and fetch
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "Persistent User"
        assert user.role == "user"
        assert user.status == "active"
        assert user.id is not None
