"""Pytest fixtures and configuration."""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi_app.core.config import settings
from fastapi_app.core.rate_limit import ALL_LIMITERS
from fastapi_app.db.session import engine
from fastapi_app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an asynchronous HTTP test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def dispose_db_engine() -> AsyncGenerator[None, None]:
    """Ensure async engine connections are cleanly disposed between test runs."""
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
def rate_limits_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suites register many users from one address; security tests turn limits back on."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    for limiter in ALL_LIMITERS:
        limiter.reset()
