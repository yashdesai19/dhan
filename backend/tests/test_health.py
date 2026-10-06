"""Test health endpoints."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: httpx.AsyncClient) -> None:
    """Test that GET /health returns { 'status': 'ok' } with HTTP 200."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: httpx.AsyncClient) -> None:
    """Test that GET /api/v1/health returns { 'status': 'ok' } with HTTP 200."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
