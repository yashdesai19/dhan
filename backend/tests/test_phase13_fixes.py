"""Phase 13: profile editing, password reset, group-expense payments, and the stored split method."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import update

from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.token import PasswordResetToken
from fastapi_app.services import auth as auth_service

PW = "SecurePassword123!"


async def register(client: httpx.AsyncClient, name: str) -> tuple[dict, dict, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}@dhan.com"
    resp = await client.post("/auth/register", json={"name": name, "email": email, "password": PW})
    assert resp.status_code == 201, resp.text
    return resp.json()["user"], {"Authorization": f"Bearer {resp.json()['access_token']}"}, email


async def post(client: httpx.AsyncClient, headers: dict, url: str, body: dict) -> dict:
    resp = await client.post(url, headers=headers, json=body)
    assert resp.status_code in (200, 201), (url, resp.text)
    return resp.json()


@pytest.mark.asyncio
async def test_01_profile_name_can_be_changed_not_role(async_client: httpx.AsyncClient) -> None:
    _, headers, _ = await register(async_client, "Profile User")
    resp = await async_client.patch(
        "/auth/me", headers=headers, json={"name": "  New Name ", "role": "admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name" and resp.json()["role"] == "user"
    assert (
        await async_client.patch("/auth/me", headers=headers, json={"name": " "})
    ).status_code == 422
    assert (await async_client.patch("/auth/me", json={"name": "Anon"})).status_code == 401


@pytest.mark.asyncio
async def test_02_password_reset(
    async_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        auth_service, "send_password_reset", lambda email, token: sent.append((email, token))
    )
    user, _, email = await register(async_client, "Reset User")
    login = await async_client.post("/auth/login", json={"email": email, "password": PW})
    old_refresh = login.json()["refresh_token"]

    known = await async_client.post("/auth/forgot-password", json={"email": email})
    unknown = await async_client.post("/auth/forgot-password", json={"email": "nobody_x@dhan.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()  # no way to tell which emails exist
    assert len(sent) == 1 and sent[0][0] == email
    code = sent[0][1]

    new_pw = "NewPassword123!"
    bad = await async_client.post(
        "/auth/reset-password", json={"token": "x" * 20, "new_password": new_pw}
    )
    assert bad.status_code == 400
    ok = await async_client.post(
        "/auth/reset-password", json={"token": code, "new_password": new_pw}
    )
    assert ok.status_code == 200
    again = await async_client.post(
        "/auth/reset-password", json={"token": code, "new_password": "Other123456!"}
    )
    assert again.status_code == 400  # single use

    old = await async_client.post("/auth/login", json={"email": email, "password": PW})
    assert old.status_code == 401
    new = await async_client.post("/auth/login", json={"email": email, "password": new_pw})
    assert new.status_code == 200
    # Sessions from before the reset are over
    stale = await async_client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert stale.status_code == 401

    # Expired codes don't work
    await async_client.post("/auth/forgot-password", json={"email": email})
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == uuid.UUID(user["id"]))
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await db.commit()
    expired = await async_client.post(
        "/auth/reset-password", json={"token": sent[-1][1], "new_password": "Another123!"}
    )
    assert expired.status_code == 400


@pytest.mark.asyncio
async def test_03_paying_a_group_expense_moves_the_account_not_spending(
    async_client: httpx.AsyncClient,
) -> None:
    me, me_h, _ = await register(async_client, "Payer")
    friend, _, _ = await register(async_client, "Payer Friend")
    acc = await post(async_client, me_h, "/accounts", {"name": "HDFC", "balance": "10000"})
    group = await post(async_client, me_h, "/groups", {"name": "Goa", "member_ids": [friend["id"]]})

    expense = await post(
        async_client,
        me_h,
        "/splits",
        {
            "group_id": group["id"],
            "title": "Villa",
            "amount": "1200",
            "split_type": "exact",
            "member_ids": [me["id"], friend["id"]],
            "exact": {me["id"]: "300", friend["id"]: "900"},
            "display_method": "shares",
            "account_id": acc["id"],
        },
    )
    assert expense["display_method"] == "shares"
    listed = (await async_client.get("/splits", headers=me_h)).json()
    assert listed[0]["display_method"] == "shares"

    account = (await async_client.get(f"/accounts/{acc['id']}", headers=me_h)).json()
    assert Decimal(account["balance"]) == Decimal("8800")
    txs = (await async_client.get("/transactions", headers=me_h)).json()
    assert [(t["type"], t["split_expense_id"]) for t in txs] == [("split", expense["id"])]
    month = datetime.now(UTC).strftime("%Y-%m")
    report = (await async_client.get(f"/reports/monthly?month={month}&tz=UTC", headers=me_h)).json()
    assert Decimal(report["spent"]) == 0  # your share counts once settled, not here

    # The payment can't be edited on its own...
    tx_id = txs[0]["id"]
    patch = await async_client.patch(f"/transactions/{tx_id}", headers=me_h, json={"amount": "1"})
    assert patch.status_code == 400
    assert (await async_client.delete(f"/transactions/{tx_id}", headers=me_h)).status_code == 400
    # ...but deleting the expense puts the money back
    assert (await async_client.delete(f"/splits/{expense['id']}", headers=me_h)).status_code == 204
    account = (await async_client.get(f"/accounts/{acc['id']}", headers=me_h)).json()
    assert Decimal(account["balance"]) == Decimal("10000")
    assert (await async_client.get("/transactions", headers=me_h)).json() == []


@pytest.mark.asyncio
async def test_04_only_your_own_account_and_payment(async_client: httpx.AsyncClient) -> None:
    _, me_h, _ = await register(async_client, "Acct Me")
    friend, friend_h, _ = await register(async_client, "Acct Friend")
    friend_acc = await post(
        async_client, friend_h, "/accounts", {"name": "Friend Bank", "balance": "500"}
    )
    my_acc = await post(async_client, me_h, "/accounts", {"name": "Mine", "balance": "500"})
    group = await post(async_client, me_h, "/groups", {"name": "G", "member_ids": [friend["id"]]})
    base = {"group_id": group["id"], "title": "x", "amount": "100"}
    foreign = await async_client.post(
        "/splits", headers=me_h, json={**base, "account_id": friend_acc["id"]}
    )
    assert foreign.status_code == 404
    not_payer = await async_client.post(
        "/splits",
        headers=me_h,
        json={**base, "paid_by_id": friend["id"], "account_id": my_acc["id"]},
    )
    assert not_payer.status_code == 400
    friend_view = (await async_client.get(f"/accounts/{friend_acc['id']}", headers=friend_h)).json()
    assert Decimal(friend_view["balance"]) == Decimal("500")


@pytest.mark.asyncio
async def test_05_net_worth_history_is_recorded_per_user(async_client: httpx.AsyncClient) -> None:
    _, me_h, _ = await register(async_client, "Snap Me")
    _, other_h, _ = await register(async_client, "Snap Other")
    await post(async_client, me_h, "/accounts", {"name": "Bank", "balance": "1500"})
    assert (await async_client.get("/net-worth/history", headers=me_h)).json() == []
    await async_client.get("/net-worth", headers=me_h)
    await post(
        async_client, me_h, "/accounts", {"name": "Wallet", "type": "wallet", "balance": "500"}
    )
    await async_client.get("/net-worth", headers=me_h)  # same month: updated, not duplicated
    history = (await async_client.get("/net-worth/history", headers=me_h)).json()
    assert len(history) == 1 and Decimal(history[0]["net_worth"]) == Decimal("2000")
    assert (await async_client.get("/net-worth/history", headers=other_h)).json() == []


@pytest.mark.asyncio
async def test_06_ai_answers_who_owes_whom(async_client: httpx.AsyncClient) -> None:
    me, me_h, _ = await register(async_client, "Ai Splitter")
    friend, _, friend_email = await register(async_client, "Ai Friend")
    group = await post(
        async_client, me_h, "/groups", {"name": "Trip", "member_ids": [friend["id"]]}
    )

    async def ask(question: str) -> dict:
        conversation = await post(async_client, me_h, "/ai/conversations", {})
        reply = await post(
            async_client,
            me_h,
            f"/ai/conversations/{conversation['id']}/messages",
            {"content": question},
        )
        return reply["assistant_message"]

    square = await ask("How much do people owe me?")
    assert square["intent"] == "splits" and "all square" in square["content"]

    await post(
        async_client,
        me_h,
        "/splits",
        {"group_id": group["id"], "title": "Villa", "amount": "1200", "split_type": "equal"},
    )
    owed = await ask("Who owes me money?")
    assert owed["intent"] == "splits"
    assert "Ai Friend" in owed["content"] and "600" in owed["content"]
    assert friend_email not in owed["content"] and friend["id"] not in owed["content"]
