"""The update prompt learns the newest APK from downloads/version.json."""

import json

import httpx
import pytest

from fastapi_app.main import STATIC_DIR


@pytest.mark.asyncio
async def test_app_version_matches_published_file(async_client: httpx.AsyncClient) -> None:
    published = json.loads((STATIC_DIR / "downloads" / "version.json").read_text(encoding="utf-8"))
    for path in ("/app-version", "/api/v1/app-version"):
        body = (await async_client.get(path)).json()
        assert body["latest_version"] == published["latest_version"]
        assert body["min_version"] == published["min_version"]
        assert body["download_url"].endswith("/downloads/dhan.apk")
        assert body["force_update"] is False
