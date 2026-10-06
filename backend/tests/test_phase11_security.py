"""Phase 11 security tests for the FastAPI backend.

1. Cross-user isolation: a second user attacks every kind of resource the first one owns
2. Admin authorization: role comes from the database, never from the token
3. JWT handling: tampering, wrong algorithm/secret, wrong token type, expiry, disabled users
4. Refresh tokens: single use with reuse detection, logout scoped to the caller
5. Passwords: bcrypt storage, never returned, 72-byte limit
6. Rate limiting: login guessing, sign-up floods, AI questions
7. Error responses: no stack traces or internals in production mode
8. CORS and security headers; production configuration guard
9. Injection and mass assignment; database integrity constraints
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import jwt
import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from fastapi_app.core.config import INSECURE_DEV_SECRET, Settings, settings
from fastapi_app.db.session import AsyncSessionLocal, get_db
from fastapi_app.main import app, enforce_production_settings
from fastapi_app.models.user import User

TODAY = datetime.now(UTC).date()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register(
    client: httpx.AsyncClient, name: str, password: str = "SecurePassword123!"
) -> tuple[dict, dict, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}@dhan.com"
    resp = await client.post(
        "/auth/register", json={"name": name, "email": email, "password": password}
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    data["user"]["refresh_token"] = data["refresh_token"]
    return data["user"], {"Authorization": f"Bearer {data['access_token']}"}, email


async def post(client: httpx.AsyncClient, headers: dict, url: str, body: dict) -> dict:
    resp = await client.post(url, headers=headers, json=body)
    assert resp.status_code in (200, 201), (url, resp.text)
    return resp.json()


async def set_user(user_id: str, **values: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(update(User).where(User.id == uuid.UUID(user_id)).values(**values))
        await db.commit()


def forge(payload: dict, key: str | None = None, algorithm: str = "HS256") -> str:
    return jwt.encode(payload, key if key is not None else settings.JWT_SECRET_KEY, algorithm)


def claims(user_id: str, **extra: object) -> dict:
    now = datetime.now(UTC)
    return {
        "sub": user_id,
        "type": "access",
        "role": "user",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        **extra,
    }


async def owned_world(client: httpx.AsyncClient) -> dict:
    """One of everything, owned by a fresh user."""
    user, headers, email = await register(client, "Victim")
    acc = await post(client, headers, "/accounts", {"name": "Victim Bank", "balance": "100000"})
    acc2 = await post(client, headers, "/accounts", {"name": "Victim Wallet", "type": "wallet"})
    cat = await post(
        client, headers, "/categories", {"name": "Victim Cat", "category_type": "expense"}
    )
    tx = await post(
        client,
        headers,
        "/transactions",
        {"account_id": acc["id"], "amount": "500", "type": "expense", "category_id": cat["id"]},
    )
    budget = await post(client, headers, "/budgets", {"amount": "9000", "month": f"{TODAY:%Y-%m}"})
    goal = await post(
        client,
        headers,
        "/goals",
        {"name": "Victim Goal", "target_amount": "5000", "target_date": "2030-01-01"},
    )
    goal = await post(client, headers, f"/goals/{goal['id']}/contributions", {"amount": "100"})
    recurring = await post(
        client,
        headers,
        "/recurring",
        {
            "title": "Victim Rent",
            "amount": "700",
            "account_id": acc["id"],
            "next_due_date": "2030-01-05",
        },
    )
    asset = await post(
        client,
        headers,
        "/net-worth/assets",
        {"name": "Gold", "asset_type": "gold", "current_value": "10"},
    )
    loan = await post(
        client,
        headers,
        "/net-worth/liabilities",
        {"name": "Loan", "liability_type": "other", "total_amount": "10", "remaining_amount": "5"},
    )
    friend, friend_headers, _ = await register(client, "Victim Friend")
    group = await post(
        client, headers, "/groups", {"name": "Victim Trip", "member_ids": [friend["id"]]}
    )
    expense = await post(
        client,
        headers,
        "/splits",
        {"group_id": group["id"], "title": "Villa", "amount": "1000"},
    )
    conversation = await post(client, headers, "/ai/conversations", {"title": "Private"})
    return {
        "user": user,
        "headers": headers,
        "email": email,
        "friend": friend,
        "account": acc,
        "account2": acc2,
        "category": cat,
        "transaction": tx,
        "budget": budget,
        "goal": goal,
        "recurring": recurring,
        "asset": asset,
        "loan": loan,
        "group": group,
        "expense": expense,
        "conversation": conversation,
    }


# ==============================================================================
# 1. CROSS-USER ISOLATION
# ==============================================================================


@pytest.mark.asyncio
async def test_01_other_user_cannot_read_or_modify_anything(
    async_client: httpx.AsyncClient,
) -> None:
    w = await owned_world(async_client)
    _, attacker, _ = await register(async_client, "Attacker")

    a, c, t = w["account"]["id"], w["category"]["id"], w["transaction"]["id"]
    b, g, r = w["budget"]["id"], w["goal"]["id"], w["recurring"]["id"]
    s, gr, e = w["asset"]["id"], w["group"]["id"], w["expense"]["id"]
    loan, conv = w["loan"]["id"], w["conversation"]["id"]
    contribution = w["goal"]["contributions"][0]["id"]

    attacks = [
        ("GET", f"/accounts/{a}", None),
        ("PATCH", f"/accounts/{a}", {"balance": "0"}),
        ("DELETE", f"/accounts/{a}", None),
        ("POST", f"/accounts/{a}/archive", None),
        ("GET", f"/categories/{c}", None),
        ("PATCH", f"/categories/{c}", {"name": "Pwned"}),
        ("GET", f"/transactions/{t}", None),
        ("PATCH", f"/transactions/{t}", {"amount": "1"}),
        ("DELETE", f"/transactions/{t}", None),
        ("GET", f"/budgets/{b}", None),
        ("PATCH", f"/budgets/{b}", {"amount": "1"}),
        ("DELETE", f"/budgets/{b}", None),
        ("GET", f"/goals/{g}", None),
        ("PATCH", f"/goals/{g}", {"name": "Pwned"}),
        ("DELETE", f"/goals/{g}", None),
        ("POST", f"/goals/{g}/contributions", {"amount": "1"}),
        ("GET", f"/goals/{g}/contributions", None),
        ("DELETE", f"/goals/{g}/contributions/{contribution}", None),
        ("GET", f"/recurring/{r}", None),
        ("PATCH", f"/recurring/{r}", {"amount": "1"}),
        ("DELETE", f"/recurring/{r}", None),
        ("POST", f"/recurring/{r}/trigger", None),
        ("POST", f"/recurring/{r}/deactivate", None),
        ("POST", f"/recurring/{r}/activate", None),
        ("PATCH", f"/net-worth/assets/{s}", {"current_value": "0"}),
        ("DELETE", f"/net-worth/assets/{s}", None),
        ("PATCH", f"/net-worth/liabilities/{loan}", {"remaining_amount": "0"}),
        ("DELETE", f"/net-worth/liabilities/{loan}", None),
        ("GET", f"/groups/{gr}", None),
        ("PATCH", f"/groups/{gr}", {"name": "Pwned"}),
        ("DELETE", f"/groups/{gr}", None),
        ("GET", f"/groups/{gr}/balances", None),
        ("POST", f"/groups/{gr}/members", {"user_id": str(uuid.uuid4())}),
        ("DELETE", f"/groups/{gr}/members/{w['friend']['id']}", None),
        ("GET", f"/splits/{e}", None),
        ("PATCH", f"/splits/{e}", {"title": "Pwned"}),
        ("DELETE", f"/splits/{e}", None),
        ("GET", f"/ai/conversations/{conv}", None),
        ("POST", f"/ai/conversations/{conv}/messages", {"content": "What's my balance?"}),
        ("DELETE", f"/ai/conversations/{conv}", None),
    ]
    for method, url, body in attacks:
        resp = await async_client.request(method, url, headers=attacker, json=body)
        assert resp.status_code in (403, 404), (method, url, resp.status_code, resp.text)

    # Nothing of the victim's is visible in the attacker's lists or totals
    for url in (
        "/accounts",
        "/transactions",
        "/budgets",
        "/goals",
        "/recurring",
        "/groups",
        "/net-worth/assets",
        "/net-worth/liabilities",
        "/ai/conversations",
    ):
        body = (await async_client.get(url, headers=attacker)).json()
        assert w["user"]["id"] not in str(body) and "Victim" not in str(body), url
    assert (await async_client.get("/people", headers=attacker)).json() == []
    balances = (await async_client.get("/splits/balances", headers=attacker)).json()
    assert Decimal(balances["owed"]) == 0 and Decimal(balances["owe"]) == 0

    # ...and everything of the victim's is exactly as it was
    victim = w["headers"]
    assert Decimal(
        (await async_client.get(f"/accounts/{a}", headers=victim)).json()["balance"]
    ) == Decimal("99500")
    assert (await async_client.get(f"/transactions/{t}", headers=victim)).json()[
        "amount"
    ] == "500.00"
    assert (await async_client.get(f"/goals/{g}", headers=victim)).json()["name"] == "Victim Goal"
    assert (await async_client.get(f"/recurring/{r}", headers=victim)).json()["status"] == "active"
    group = (await async_client.get(f"/groups/{gr}", headers=victim)).json()
    assert group["name"] == "Victim Trip" and len(group["members"]) == 2
    conversation = (await async_client.get(f"/ai/conversations/{conv}", headers=victim)).json()
    assert conversation["message_count"] == 0


@pytest.mark.asyncio
async def test_02_other_users_ids_cannot_be_borrowed(async_client: httpx.AsyncClient) -> None:
    """Referencing someone else's account, category or group in your own records fails."""
    w = await owned_world(async_client)
    _, attacker, _ = await register(async_client, "Borrower")
    own = await post(async_client, attacker, "/accounts", {"name": "Mine", "balance": "10"})

    attempts = [
        ("/transactions", {"account_id": w["account"]["id"], "amount": "1", "type": "income"}),
        (
            "/transactions",
            {
                "account_id": own["id"],
                "amount": "1",
                "type": "transfer",
                "destination_account_id": w["account"]["id"],
            },
        ),
        (
            "/transactions",
            {
                "account_id": own["id"],
                "amount": "1",
                "type": "expense",
                "category_id": w["category"]["id"],
            },
        ),
        (
            "/recurring",
            {
                "title": "x",
                "amount": "1",
                "account_id": w["account"]["id"],
                "next_due_date": "2030-01-01",
            },
        ),
        (
            "/goals",
            {
                "name": "x",
                "target_amount": "10",
                "target_date": "2030-01-01",
                "initial_amount": "1",
                "account_id": w["account"]["id"],
            },
        ),
        (
            "/budgets/category",
            {"amount": "5", "category_id": w["category"]["id"], "month": f"{TODAY:%Y-%m}"},
        ),
        ("/splits", {"group_id": w["group"]["id"], "title": "x", "amount": "10"}),
        (
            "/settlements",
            {"group_id": w["group"]["id"], "payee_id": w["user"]["id"], "amount": "1"},
        ),
    ]
    for url, body in attempts:
        resp = await async_client.post(url, headers=attacker, json=body)
        assert resp.status_code in (400, 403, 404, 422), (url, resp.status_code, resp.text)

    victim_account = (
        await async_client.get(f"/accounts/{w['account']['id']}", headers=w["headers"])
    ).json()
    assert Decimal(victim_account["balance"]) == Decimal("99500")


@pytest.mark.asyncio
async def test_03_cannot_join_or_seed_someone_elses_group(async_client: httpx.AsyncClient) -> None:
    """Regression: anyone could add themselves to any group and then read it."""
    w = await owned_world(async_client)
    attacker, attacker_headers, attacker_email = await register(async_client, "Group Crasher")
    gid = w["group"]["id"]

    for body in ({"user_id": attacker["id"]}, {"email": attacker_email}):
        resp = await async_client.post(
            f"/groups/{gid}/members", headers=attacker_headers, json=body
        )
        assert resp.status_code == 404, resp.text
    assert (await async_client.get(f"/groups/{gid}", headers=attacker_headers)).status_code in (
        403,
        404,
    )

    # The creator still can
    victim = w["headers"]
    added = await async_client.post(
        f"/groups/{gid}/members", headers=victim, json={"user_id": attacker["id"]}
    )
    assert added.status_code in (200, 201)


@pytest.mark.asyncio
async def test_04_split_expenses_cannot_create_debts_for_strangers(
    async_client: httpx.AsyncClient,
) -> None:
    alice, alice_h, _ = await register(async_client, "Split Alice")
    bob, _, _ = await register(async_client, "Split Bob")
    carol, carol_h, _ = await register(async_client, "Split Carol")

    # Outside a group, Alice can't say Bob paid for Carol
    resp = await async_client.post(
        "/splits",
        headers=alice_h,
        json={
            "title": "Fake",
            "amount": "900",
            "paid_by_id": bob["id"],
            "member_ids": [bob["id"], carol["id"]],
        },
    )
    assert resp.status_code == 400
    # In her group, she can't include people who aren't members
    group = await post(async_client, alice_h, "/groups", {"name": "Alice only"})
    resp = await async_client.post(
        "/splits",
        headers=alice_h,
        json={
            "group_id": group["id"],
            "title": "Fake",
            "amount": "900",
            "member_ids": [alice["id"], carol["id"]],
        },
    )
    assert resp.status_code == 400
    carol_balances = (await async_client.get("/splits/balances", headers=carol_h)).json()
    assert Decimal(carol_balances["owe"]) == 0


# ==============================================================================
# 2. ADMIN AUTHORIZATION
# ==============================================================================


@pytest.mark.asyncio
async def test_05_admin_role_comes_from_the_database(async_client: httpx.AsyncClient) -> None:
    user, headers, _ = await register(async_client, "Role User")
    assert (await async_client.get("/auth/admin-only", headers=headers)).status_code == 403

    # A token claiming admin, even correctly signed, grants nothing by itself
    admin_claim = {"Authorization": f"Bearer {forge(claims(user['id'], role='admin'))}"}
    assert (await async_client.get("/auth/admin-only", headers=admin_claim)).status_code == 403

    # Registration ignores a requested role
    sneaky = await async_client.post(
        "/auth/register",
        json={
            "name": "Sneaky",
            "email": f"sneaky_{uuid.uuid4().hex[:6]}@dhan.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )
    assert sneaky.json()["user"]["role"] == "user"

    await set_user(user["id"], role="admin")
    assert (await async_client.get("/auth/admin-only", headers=headers)).status_code == 200
    await set_user(user["id"], role="user")
    # Demotion takes effect on the very next request, with the same token
    assert (await async_client.get("/auth/admin-only", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_06_admins_get_no_backdoor_into_user_data(async_client: httpx.AsyncClient) -> None:
    """Being an admin doesn't open other users' records through the API."""
    w = await owned_world(async_client)
    admin, admin_h, _ = await register(async_client, "API Admin")
    await set_user(admin["id"], role="admin")
    for url in (
        f"/accounts/{w['account']['id']}",
        f"/goals/{w['goal']['id']}",
        f"/transactions/{w['transaction']['id']}",
        f"/ai/conversations/{w['conversation']['id']}",
    ):
        assert (await async_client.get(url, headers=admin_h)).status_code in (403, 404), url


# ==============================================================================
# 3. JWT HANDLING
# ==============================================================================


@pytest.mark.asyncio
async def test_07_forged_and_malformed_tokens_are_rejected(async_client: httpx.AsyncClient) -> None:
    user, headers, _ = await register(async_client, "JWT User")
    uid = user["id"]
    real = headers["Authorization"].split()[1]
    header, payload, signature = real.split(".")
    flipped = signature[:-2] + ("AA" if signature[-2:] != "AA" else "BB")
    expired = claims(uid)
    expired["exp"] = int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())

    bad_tokens = {
        "tampered signature": f"{header}.{payload}.{flipped}",
        "alg none": jwt.encode(claims(uid), key="", algorithm="none"),
        "wrong secret": forge(claims(uid), key="x" * 48),
        "HS512 with same secret": forge(claims(uid), algorithm="HS512"),
        "expired": forge(expired),
        "refresh used as access": user["refresh_token"],
        "no sub": forge({k: v for k, v in claims(uid).items() if k != "sub"}),
        "no exp": forge({k: v for k, v in claims(uid).items() if k != "exp"}),
        "unknown user": forge(claims(str(uuid.uuid4()))),
        "garbage": "not.a.jwt",
    }
    for name, token in bad_tokens.items():
        resp = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401, name
        assert "Traceback" not in resp.text

    assert (await async_client.get("/auth/me", headers={"Authorization": real})).status_code == 401
    assert (await async_client.get("/auth/me", headers=headers)).status_code == 200


@pytest.mark.asyncio
async def test_08_disabled_users_are_locked_out(async_client: httpx.AsyncClient) -> None:
    user, headers, email = await register(async_client, "Disabled User")
    await set_user(user["id"], status="disabled")
    assert (await async_client.get("/auth/me", headers=headers)).status_code == 403
    login = await async_client.post(
        "/auth/login", json={"email": email, "password": "SecurePassword123!"}
    )
    assert login.status_code == 403
    refresh = await async_client.post(
        "/auth/refresh", json={"refresh_token": user["refresh_token"]}
    )
    assert refresh.status_code == 403


# ==============================================================================
# 4. REFRESH TOKENS
# ==============================================================================


@pytest.mark.asyncio
async def test_09_refresh_tokens_are_single_use(async_client: httpx.AsyncClient) -> None:
    user, _, _ = await register(async_client, "Rotation User")
    first = user["refresh_token"]

    rotated = await async_client.post("/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    second = rotated.json()["refresh_token"]
    assert second != first
    assert (
        await async_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {rotated.json()['access_token']}"}
        )
    ).status_code == 200

    # Replaying the used token is treated as theft: it fails and ends every session
    replay = await async_client.post("/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    assert (
        await async_client.post("/auth/refresh", json={"refresh_token": second})
    ).status_code == 401

    # An access token is not a refresh token
    access = rotated.json()["access_token"]
    assert (
        await async_client.post("/auth/refresh", json={"refresh_token": access})
    ).status_code == 401


@pytest.mark.asyncio
async def test_10_parallel_refreshes_issue_one_token(async_client: httpx.AsyncClient) -> None:
    user, _, _ = await register(async_client, "Race Refresh User")
    results = await asyncio.gather(
        *(
            async_client.post("/auth/refresh", json={"refresh_token": user["refresh_token"]})
            for _ in range(3)
        )
    )
    assert sorted(r.status_code for r in results).count(200) <= 1


@pytest.mark.asyncio
async def test_11_logout_only_revokes_your_own_tokens(async_client: httpx.AsyncClient) -> None:
    victim, _, _ = await register(async_client, "Logout Victim")
    _, attacker_h, _ = await register(async_client, "Logout Attacker")
    resp = await async_client.post(
        "/auth/logout", headers=attacker_h, json={"refresh_token": victim["refresh_token"]}
    )
    assert resp.status_code == 200
    still_valid = await async_client.post(
        "/auth/refresh", json={"refresh_token": victim["refresh_token"]}
    )
    assert still_valid.status_code == 200


# ==============================================================================
# 5. PASSWORDS
# ==============================================================================


@pytest.mark.asyncio
async def test_12_password_storage_and_exposure(async_client: httpx.AsyncClient) -> None:
    user, headers, email = await register(async_client, "Password User")
    responses = [
        (await async_client.get("/auth/me", headers=headers)).text,
        (
            await async_client.post(
                "/auth/login", json={"email": email, "password": "SecurePassword123!"}
            )
        ).text,
    ]
    for body in responses:
        assert "password_hash" not in body and '"password"' not in body and "$2b$" not in body

    async with AsyncSessionLocal() as db:
        stored = await db.scalar(select(User.password_hash).where(User.id == uuid.UUID(user["id"])))
    assert stored.startswith("$2b$12$") and "SecurePassword123!" not in stored


@pytest.mark.asyncio
async def test_13_bcrypt_byte_limit(async_client: httpx.AsyncClient) -> None:
    """Regression: a 73-128 character password crashed registration with a 500."""
    for password in ("a" * 73, "é" * 37, "a" * 128):
        resp = await async_client.post(
            "/auth/register",
            json={
                "name": "Long Pw",
                "email": f"long_{uuid.uuid4().hex[:6]}@dhan.com",
                "password": password,
            },
        )
        assert resp.status_code == 422, password[:3]
    _, _, email = await register(async_client, "Max Pw", password="b" * 72)
    ok = await async_client.post("/auth/login", json={"email": email, "password": "b" * 72})
    assert ok.status_code == 200
    long_login = await async_client.post(
        "/auth/login", json={"email": email, "password": "b" * 500}
    )
    assert long_login.status_code == 401


# ==============================================================================
# 6. RATE LIMITING
# ==============================================================================


@pytest.fixture
def rate_limits_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)


@pytest.mark.asyncio
async def test_14_password_guessing_is_throttled(
    async_client: httpx.AsyncClient, rate_limits_on
) -> None:
    _, _, email = await register(async_client, "Guess Target")
    for _ in range(5):
        resp = await async_client.post(
            "/auth/login", json={"email": email, "password": "wrong-guess"}
        )
        assert resp.status_code == 401
    locked = await async_client.post(
        "/auth/login", json={"email": email, "password": "wrong-guess"}
    )
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    # While locked, even the right password is not checked
    right = await async_client.post(
        "/auth/login", json={"email": email, "password": "SecurePassword123!"}
    )
    assert right.status_code == 429


@pytest.mark.asyncio
async def test_15_signup_floods_are_throttled(
    async_client: httpx.AsyncClient, rate_limits_on
) -> None:
    codes = []
    for n in range(11):
        resp = await async_client.post(
            "/auth/register",
            json={
                "name": "Flood",
                "email": f"flood{n}_{uuid.uuid4().hex[:6]}@dhan.com",
                "password": "SecurePassword123!",
            },
        )
        codes.append(resp.status_code)
    assert codes[:10] == [201] * 10 and codes[10] == 429


@pytest.mark.asyncio
async def test_16_ai_questions_are_throttled(async_client: httpx.AsyncClient, monkeypatch) -> None:
    _, headers, _ = await register(async_client, "AI Flood")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    conv = await post(async_client, headers, "/ai/conversations", {})
    codes = []
    for _ in range(31):
        resp = await async_client.post(
            f"/ai/conversations/{conv['id']}/messages",
            headers=headers,
            json={"content": "Balance?"},
        )
        codes.append(resp.status_code)
    assert codes[:30] == [201] * 30 and codes[30] == 429


# ==============================================================================
# 7. ERROR RESPONSES
# ==============================================================================


@pytest.mark.asyncio
async def test_17_unexpected_errors_reveal_nothing(async_client: httpx.AsyncClient) -> None:
    async def broken_db():  # type: ignore[no-untyped-def]
        raise RuntimeError("connect to postgresql://dhan_user:hunter2@db failed")
        yield  # pragma: no cover

    was_debug = app.debug
    app.debug = False  # production behaviour
    app.middleware_stack = None  # rebuilt on the next request with debug off
    app.dependency_overrides[get_db] = broken_db
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.debug = was_debug
        app.middleware_stack = None
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error."}
    for leak in ("Traceback", "hunter2", "postgresql", "RuntimeError", 'File "'):
        assert leak not in resp.text


@pytest.mark.asyncio
async def test_18_client_errors_are_plain(async_client: httpx.AsyncClient) -> None:
    _, headers, _ = await register(async_client, "Errors User")
    missing = await async_client.get(f"/accounts/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404 and set(missing.json()) == {"detail"}
    wrong_login = await async_client.post(
        "/auth/login", json={"email": "nobody@dhan.com", "password": "x"}
    )
    # Same answer whether or not the email exists
    assert wrong_login.json() == {"detail": "Invalid email or password."}


# ==============================================================================
# 8. CORS, HEADERS, PRODUCTION CONFIG
# ==============================================================================


@pytest.mark.asyncio
async def test_19_cors_and_security_headers(async_client: httpx.AsyncClient) -> None:
    preflight = await async_client.options(
        "/accounts",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert preflight.headers.get("access-control-allow-credentials") != "true"

    resp = await async_client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["cache-control"] == "no-store"


def test_20_production_refuses_unsafe_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    unsafe = Settings(ENVIRONMENT="production", DEBUG=True, _env_file=None)
    problems = unsafe.production_problems()
    assert any("DEBUG" in p for p in problems)
    assert any("JWT_SECRET_KEY" in p for p in problems)
    assert any("CORS" in p for p in problems)
    assert any("DATABASE_URL" in p for p in problems)
    with pytest.raises(RuntimeError, match="Refusing to start in production"):
        enforce_production_settings(unsafe)

    safe = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="k" * 64,
        SECRET_KEY="s" * 64,
        FASTAPI_CORS_ORIGINS=["https://app.dhan.example"],
        DATABASE_URL="postgresql+asyncpg://dhan:strong-secret@db:5432/dhan",
        _env_file=None,
    )
    assert safe.production_problems() == []
    enforce_production_settings(safe)
    # Development is unaffected
    enforce_production_settings(Settings(ENVIRONMENT="development", _env_file=None))
    # Debug is opt-in (Django's settings may have loaded the dev .env into the environment)
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).DEBUG is False
    assert INSECURE_DEV_SECRET not in safe.JWT_SECRET_KEY


# ==============================================================================
# 9. INJECTION, MASS ASSIGNMENT, CONSTRAINTS
# ==============================================================================


@pytest.mark.asyncio
async def test_21_injection_payloads_are_data(async_client: httpx.AsyncClient) -> None:
    w = await owned_world(async_client)
    _, headers, _ = await register(async_client, "Injector")
    acc = await post(async_client, headers, "/accounts", {"name": "Robert'); DROP TABLE users;--"})
    await post(
        async_client,
        headers,
        "/transactions",
        {"account_id": acc["id"], "amount": "1", "type": "expense", "description": "' OR '1'='1"},
    )
    for term in ("' OR '1'='1", "%", "_", "Victim", "%' OR 1=1 --"):
        resp = await async_client.get("/transactions", headers=headers, params={"search": term})
        assert resp.status_code == 200
        assert all(t["account_id"] == acc["id"] for t in resp.json())
    assert (
        (await async_client.get("/accounts", headers=headers))
        .json()[0]["name"]
        .startswith("Robert'")
    )
    assert (
        await async_client.get(f"/accounts/{w['account']['id']}", headers=w["headers"])
    ).status_code == 200


@pytest.mark.asyncio
async def test_22_mass_assignment_is_ignored(async_client: httpx.AsyncClient) -> None:
    victim, _, _ = await register(async_client, "MA Victim")
    _, headers, _ = await register(async_client, "MA Attacker")
    acc = await post(
        async_client,
        headers,
        "/accounts",
        {"name": "Mine", "user_id": victim["id"], "id": str(uuid.uuid4())},
    )
    me = (await async_client.get("/auth/me", headers=headers)).json()
    assert acc["user_id"] == me["id"]
    tx = await post(
        async_client,
        headers,
        "/transactions",
        {
            "account_id": acc["id"],
            "amount": "1",
            "type": "income",
            "user_id": victim["id"],
            "status": "pending",
        },
    )
    assert tx["user_id"] == me["id"] and tx["status"] == "completed"


@pytest.mark.asyncio
async def test_23_database_rejects_impossible_values() -> None:
    async with AsyncSessionLocal() as db:
        for statement in (
            "UPDATE users SET role = 'superadmin' WHERE id = (SELECT id FROM users LIMIT 1)",
            "UPDATE users SET status = 'godmode' WHERE id = (SELECT id FROM users LIMIT 1)",
            "UPDATE dhan_transactions SET amount = -5 WHERE id = (SELECT id FROM dhan_transactions LIMIT 1)",
            "UPDATE dhan_goals SET current_amount = -1 WHERE id = (SELECT id FROM dhan_goals LIMIT 1)",
        ):
            with pytest.raises(IntegrityError):
                await db.execute(text(statement))
            await db.rollback()

    # Emails are unique regardless of case
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User.email).limit(1))
        db.add(
            User(
                name="Dup", email=existing.upper(), password_hash="x", role="user", status="active"
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()


def test_hosted_database_urls_use_the_async_driver() -> None:
    for given in ("postgres://u:p@db:5432/dhan", "postgresql://u:p@db:5432/dhan"):
        assert Settings(DATABASE_URL=given).DATABASE_URL == "postgresql+asyncpg://u:p@db:5432/dhan"
    already = "postgresql+asyncpg://u:p@db:5432/dhan"
    assert Settings(DATABASE_URL=already).DATABASE_URL == already
