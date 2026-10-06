"""Phase 12: endpoints added for the mobile app (listing splits and settlements, undoing and
receiving settlements), including their user isolation."""

import uuid
from decimal import Decimal

import httpx
import pytest


async def register(client: httpx.AsyncClient, name: str) -> tuple[dict, dict]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}@dhan.com"
    resp = await client.post(
        "/auth/register", json={"name": name, "email": email, "password": "SecurePassword123!"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["user"], {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def post(client: httpx.AsyncClient, headers: dict, url: str, body: dict) -> dict:
    resp = await client.post(url, headers=headers, json=body)
    assert resp.status_code in (200, 201), (url, resp.text)
    return resp.json()


@pytest.mark.asyncio
async def test_01_lists_show_only_the_callers_splits_and_settlements(
    async_client: httpx.AsyncClient,
) -> None:
    me, me_h = await register(async_client, "List Me")
    friend, friend_h = await register(async_client, "List Friend")
    stranger, stranger_h = await register(async_client, "List Stranger")

    group = await post(
        async_client, me_h, "/groups", {"name": "Trip", "member_ids": [friend["id"]]}
    )
    expense = await post(
        async_client, me_h, "/splits", {"group_id": group["id"], "title": "Villa", "amount": "1200"}
    )
    settlement = await post(
        async_client, friend_h, "/settlements", {"payee_id": me["id"], "amount": "100"}
    )
    # Something the stranger does elsewhere
    other_group = await post(async_client, stranger_h, "/groups", {"name": "Elsewhere"})
    await post(
        async_client,
        stranger_h,
        "/splits",
        {"group_id": other_group["id"], "title": "X", "amount": "50"},
    )

    for headers in (me_h, friend_h):
        splits = (await async_client.get("/splits", headers=headers)).json()
        assert [s["id"] for s in splits] == [expense["id"]]
        assert Decimal(splits[0]["shares"][me["id"]]) == Decimal("600.00")
        settlements = (await async_client.get("/settlements", headers=headers)).json()
        assert [s["id"] for s in settlements] == [settlement["id"]]

    stranger_splits = (await async_client.get("/splits", headers=stranger_h)).json()
    assert expense["id"] not in {s["id"] for s in stranger_splits}
    assert (await async_client.get("/settlements", headers=stranger_h)).json() == []
    assert (await async_client.get("/settlements")).status_code == 401


@pytest.mark.asyncio
async def test_02_settlements_can_be_received_and_undone(async_client: httpx.AsyncClient) -> None:
    me, me_h = await register(async_client, "Recv Me")
    friend, friend_h = await register(async_client, "Recv Friend")
    _, stranger_h = await register(async_client, "Recv Stranger")
    group = await post(
        async_client, me_h, "/groups", {"name": "Flat", "member_ids": [friend["id"]]}
    )
    await post(
        async_client, me_h, "/splits", {"group_id": group["id"], "title": "Rent", "amount": "1000"}
    )
    # Friend owes me 500
    assert Decimal((await async_client.get("/splits/balances", headers=me_h)).json()["owed"]) == 500

    # I record that the friend paid me 200: payer is the friend, payee is me
    received = await post(
        async_client,
        me_h,
        "/settlements",
        {"payee_id": friend["id"], "amount": "200", "direction": "received", "method": "cash"},
    )
    assert (received["payer_id"], received["payee_id"]) == (friend["id"], me["id"])
    assert Decimal((await async_client.get("/splits/balances", headers=me_h)).json()["owed"]) == 300
    friend_view = (await async_client.get("/splits/balances", headers=friend_h)).json()
    assert Decimal(friend_view["owe"]) == 300

    # Only the two people involved can undo it
    resp = await async_client.delete(f"/settlements/{received['id']}", headers=stranger_h)
    assert resp.status_code == 404
    assert (
        await async_client.delete(f"/settlements/{received['id']}", headers=me_h)
    ).status_code == 204
    assert Decimal((await async_client.get("/splits/balances", headers=me_h)).json()["owed"]) == 500
    assert (
        await async_client.delete(f"/settlements/{received['id']}", headers=me_h)
    ).status_code == 404

    bad = await async_client.post(
        "/settlements",
        headers=me_h,
        json={"payee_id": friend["id"], "amount": "1", "direction": "gift"},
    )
    assert bad.status_code == 422
