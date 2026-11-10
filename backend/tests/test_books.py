"""Books: a business kept apart from personal money, with strict ownership."""

import uuid

import httpx
import pytest


async def login(client: httpx.AsyncClient, name: str) -> dict:
    resp = await client.post(
        "/auth/register",
        json={
            "name": name,
            "email": f"{name.lower()}_{uuid.uuid4().hex[:6]}@dhan.com",
            "password": "SecurePassword123!",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_book_adds_cash_account(async_client: httpx.AsyncClient) -> None:
    headers = await login(async_client, "Owner")
    book = (await async_client.post("/books", headers=headers, json={"name": "Shop"})).json()
    accounts = (await async_client.get("/accounts", headers=headers)).json()
    in_book = [a["name"] for a in accounts if a["book_id"] == book["id"]]
    assert in_book == ["Shop Cash"]
    # The cash account every new user starts with stays personal
    assert all(a["book_id"] is None for a in accounts if a["name"] != "Shop Cash")


@pytest.mark.asyncio
async def test_duplicate_book_name_rejected(async_client: httpx.AsyncClient) -> None:
    headers = await login(async_client, "Owner")
    await async_client.post("/books", headers=headers, json={"name": "Shop"})
    resp = await async_client.post("/books", headers=headers, json={"name": "shop"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_account_without_book_stays_personal(async_client: httpx.AsyncClient) -> None:
    headers = await login(async_client, "Owner")
    resp = await async_client.post("/accounts", headers=headers, json={"name": "HDFC"})
    assert resp.json()["book_id"] is None


@pytest.mark.asyncio
async def test_cannot_use_another_users_book(async_client: httpx.AsyncClient) -> None:
    alice = await login(async_client, "Alice")
    bob = await login(async_client, "Bob")
    book = (await async_client.post("/books", headers=alice, json={"name": "Shop"})).json()
    create = await async_client.post(
        "/accounts", headers=bob, json={"name": "X", "book_id": book["id"]}
    )
    assert create.status_code == 404
    account = (await async_client.post("/accounts", headers=bob, json={"name": "Y"})).json()
    patch = await async_client.patch(
        f"/accounts/{account['id']}", headers=bob, json={"book_id": book["id"]}
    )
    assert patch.status_code == 404
