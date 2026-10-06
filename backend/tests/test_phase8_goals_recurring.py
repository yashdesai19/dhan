"""Comprehensive test suite for Phase 8: DHAN Goals and Recurring Payments.

Covers:
Goals:
1. Create goal (target amount, target date, icon, initial deposit)
2. Add money (contributions tracking, atomic updates)
3. Progress metrics (saved, left, pct, months_left, monthly needed, status, pill)
4. Target reached (automatic status change to 'achieved', and back when the target moves)
5. Invalid amounts (negative/zero target, negative initial/contribution, precision, overflow)
6. User ownership (cross-user isolation, foreign accounts, contributions)
7. Update & Delete goal (cascades to contributions), undo a contribution
8. Goals summary & totals calculation

Recurring:
9. Create recurring payment (bill, emi, subscription, recurring income)
10. Edit recurring payment (PATCH title, amount, next due date, clearing fields)
11. Deactivate & activate payment (toggle status; reactivation never back-fills)
12. Date calculation & frequency cadence (daily, weekly, monthly, quarterly, yearly, month end)
13. Recurring payment ownership isolation
14. Recurring summary & subscriptions breakdown (outgoing, incoming, subscriptions, 7-day split)
15. Safe recurring execution trigger (dry run, idempotency guard, balance update, EMI progress)
16. Safe background batch execution (auto-pay opt-in, idempotent re-runs, failure isolation)

DHAN Core Invariants (spec §6, reference date 2026-09-30 as in mock/clock.ts):
17. Goals: MacBook ₹45,000 saved, 38%, ₹12,500/mo; Emergency Fund Behind;
    Kerala Trip 60% On track; Total Goals Saved = ₹98,000; Total Goals Left = ₹2,52,000;
    adding ₹12,500 to MacBook moves it to 48% and ₹10,417/mo
18. Recurring: October outgoing ₹14,391 across 9 payments; next 7 days ₹8,499;
    subscriptions ₹2,692/month, ₹32,304/year across 5 subscriptions
"""

import asyncio
import calendar
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text, update

from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.account import Account
from fastapi_app.models.goal import Goal, GoalContribution
from fastapi_app.services.goal_service import calculate_goal_progress, format_inr
from fastapi_app.services.recurring_service import (
    RecurringService,
    calculate_next_occurrence,
    effective_anchor_day,
)

SPEC_TODAY = "2026-09-30"


async def register_and_login(client: httpx.AsyncClient, name: str) -> tuple[dict, dict]:
    """Helper to register a user and return user data and auth headers."""
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@dhan.com"
    reg_resp = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "SecurePassword123!"},
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return data["user"], headers


async def create_account(
    client: httpx.AsyncClient, headers: dict, name: str, balance: str = "50000.00"
) -> dict:
    """Helper to create a bank account."""
    resp = await client.post(
        "/accounts",
        headers=headers,
        json={"name": name, "account_type": "bank", "balance": balance, "currency": "INR"},
    )
    assert resp.status_code == 201
    return resp.json()


async def create_goal(client: httpx.AsyncClient, headers: dict, **fields: str) -> dict:
    """Helper to create a goal 90 days out unless overridden."""
    payload = {
        "name": "Goal",
        "target_amount": "10000.00",
        "target_date": (date.today() + timedelta(days=90)).isoformat(),
        **fields,
    }
    resp = await client.post("/goals", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def create_recurring(
    client: httpx.AsyncClient, headers: dict, account_id: str, **fields: object
) -> dict:
    """Helper to create a monthly bill unless overridden."""
    payload = {
        "title": "Bill",
        "kind": "bill",
        "amount": "1000.00",
        "account_id": account_id,
        "frequency": "monthly",
        "next_due_date": "2026-11-01",
        **fields,
    }
    resp = await client.post("/recurring", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def account_balance(client: httpx.AsyncClient, headers: dict, account_id: str) -> Decimal:
    resp = await client.get(f"/accounts/{account_id}", headers=headers)
    assert resp.status_code == 200
    return Decimal(resp.json()["balance"])


async def list_transactions(client: httpx.AsyncClient, headers: dict) -> list[dict]:
    resp = await client.get("/transactions", headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ==============================================================================
# GOALS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_01_create_goal(async_client: httpx.AsyncClient) -> None:
    """1. Test creating a goal with valid attributes and initial deposit."""
    _, headers = await register_and_login(async_client, "Goal User 1")
    acc = await create_account(async_client, headers, "HDFC Savings", "100000.00")

    future_date = (date.today() + timedelta(days=180)).isoformat()
    resp = await async_client.post(
        "/goals",
        headers=headers,
        json={
            "name": "New Gaming Laptop",
            "target_amount": "80000.00",
            "target_date": future_date,
            "icon": "laptop",
            "initial_amount": "10000.00",
            "account_id": acc["id"],
        },
    )
    assert resp.status_code == 201
    goal = resp.json()
    assert goal["name"] == "New Gaming Laptop"
    assert Decimal(goal["target_amount"]) == Decimal("80000.00")
    assert Decimal(goal["current_amount"]) == Decimal("10000.00")
    assert goal["target_date"] == future_date
    assert goal["icon"] == "laptop"
    assert goal["status"] == "in_progress"
    assert Decimal(goal["progress"]["saved"]) == Decimal("10000.00")
    assert Decimal(goal["progress"]["left"]) == Decimal("70000.00")
    assert len(goal["contributions"]) == 1
    assert Decimal(goal["contributions"][0]["amount"]) == Decimal("10000.00")


@pytest.mark.asyncio
async def test_02_add_money(async_client: httpx.AsyncClient) -> None:
    """2. Test adding money to a goal via contributions endpoint."""
    _, headers = await register_and_login(async_client, "Goal User 2")
    acc = await create_account(async_client, headers, "SBI Savings", "50000.00")

    future_date = (date.today() + timedelta(days=200)).isoformat()
    create_resp = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Vacation Fund", "target_amount": "50000.00", "target_date": future_date},
    )
    assert create_resp.status_code == 201
    goal_id = create_resp.json()["id"]

    # Deposit 1: ₹15,000
    dep1 = await async_client.post(
        f"/goals/{goal_id}/contributions",
        headers=headers,
        json={"amount": "15000.00", "account_id": acc["id"], "notes": "First savings tranche"},
    )
    assert dep1.status_code == 200
    g1 = dep1.json()
    assert Decimal(g1["current_amount"]) == Decimal("15000.00")
    assert Decimal(g1["progress"]["left"]) == Decimal("35000.00")

    # Deposit 2 via /add-money alias: ₹10,000
    dep2 = await async_client.post(
        f"/goals/{goal_id}/add-money",
        headers=headers,
        json={"amount": "10000.00", "account_id": acc["id"], "notes": "Bonus payout deposit"},
    )
    assert dep2.status_code == 200
    g2 = dep2.json()
    assert Decimal(g2["current_amount"]) == Decimal("25000.00")
    assert Decimal(g2["progress"]["left"]) == Decimal("25000.00")
    assert g2["progress"]["pct"] == 50
    assert len(g2["contributions"]) == 2

    history = await async_client.get(f"/goals/{goal_id}/contributions", headers=headers)
    assert history.status_code == 200
    assert [Decimal(c["amount"]) for c in history.json()] == [
        Decimal("10000.00"),
        Decimal("15000.00"),
    ]


@pytest.mark.asyncio
async def test_02b_contributions_do_not_move_account_money(async_client: httpx.AsyncClient) -> None:
    """2b. Adding money is an earmark: no ledger transaction, no account balance change."""
    _, headers = await register_and_login(async_client, "Goal Earmark User")
    acc = await create_account(async_client, headers, "HDFC", "20000.00")
    goal = await create_goal(async_client, headers, target_amount="50000.00")

    resp = await async_client.post(
        f"/goals/{goal['id']}/contributions",
        headers=headers,
        json={"amount": "5000.00", "account_id": acc["id"]},
    )
    assert resp.status_code == 200
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("20000.00")
    assert await list_transactions(async_client, headers) == []


@pytest.mark.asyncio
async def test_02c_concurrent_deposits_are_not_lost(async_client: httpx.AsyncClient) -> None:
    """2c. Parallel deposits to one goal all land (row lock, no lost updates)."""
    _, headers = await register_and_login(async_client, "Goal Concurrency User")
    goal = await create_goal(async_client, headers, target_amount="5000.00")

    responses = await asyncio.gather(
        *(
            async_client.post(
                f"/goals/{goal['id']}/contributions", headers=headers, json={"amount": "100.00"}
            )
            for _ in range(8)
        )
    )
    assert all(r.status_code == 200 for r in responses)
    final = (await async_client.get(f"/goals/{goal['id']}", headers=headers)).json()
    assert Decimal(final["current_amount"]) == Decimal("800.00")
    assert len(final["contributions"]) == 8


@pytest.mark.asyncio
async def test_03_goal_progress_metrics(async_client: httpx.AsyncClient) -> None:
    """3. Test goal progress metrics (percentage, months left, monthly needed, pill)."""
    _, headers = await register_and_login(async_client, "Goal User 3")

    # Target: 60,000, 6 months out
    future_date = (date.today() + timedelta(days=180)).isoformat()
    resp = await async_client.post(
        "/goals",
        headers=headers,
        json={
            "name": "Camera Kit",
            "target_amount": "60000.00",
            "target_date": future_date,
            "initial_amount": "15000.00",
        },
    )
    assert resp.status_code == 201
    goal = resp.json()
    prog = goal["progress"]
    assert Decimal(prog["saved"]) == Decimal("15000.00")
    assert Decimal(prog["left"]) == Decimal("45000.00")
    assert prog["pct"] == 25
    assert prog["months_left"] >= 5
    assert Decimal(prog["monthly"]) > Decimal("0.00")
    assert "mo" in prog["pill"] or prog["pill"] in ["Behind", "On track"]


def test_03b_progress_rounding_matches_app() -> None:
    """3b. pct and monthly round halves up (JS Math.round), pill uses Indian digit grouping."""
    as_of = date(2026, 9, 30)
    created = datetime(2026, 9, 30, tzinfo=UTC)

    # 1 of 8 saved = 12.5% -> 13 (banker's rounding would give 12)
    eighth = Goal(
        target_amount=Decimal("8.00"),
        current_amount=Decimal("1.00"),
        target_date=date(2026, 11, 30),
        created_at=created,
        status="in_progress",
    )
    assert calculate_goal_progress(eighth, as_of).pct == 13

    # ₹5 left over 2 months = 2.5 -> 3 (banker's rounding would give 2)
    halves = Goal(
        target_amount=Decimal("5.00"),
        current_amount=Decimal("0.00"),
        target_date=date(2026, 11, 30),
        created_at=created,
        status="in_progress",
    )
    assert calculate_goal_progress(halves, as_of).monthly == Decimal("3")

    # ₹24 lakh over 12 months -> ₹2,00,000/mo (Indian grouping, not ₹200,000)
    big = Goal(
        target_amount=Decimal("2400000.00"),
        current_amount=Decimal("0.00"),
        target_date=date(2027, 9, 30),
        created_at=created,
        status="in_progress",
    )
    big_progress = calculate_goal_progress(big, as_of)
    assert big_progress.months_left == 12
    assert big_progress.pill == "₹2,00,000/mo"

    assert format_inr(0) == "₹0"
    assert format_inr(999) == "₹999"
    assert format_inr(1000) == "₹1,000"
    assert format_inr(124580) == "₹1,24,580"
    assert format_inr(12345678) == "₹1,23,45,678"


@pytest.mark.asyncio
async def test_04_target_reached(async_client: httpx.AsyncClient) -> None:
    """4. Test automatic status change to 'achieved' when goal target is reached or surpassed."""
    _, headers = await register_and_login(async_client, "Goal User 4")
    future_date = (date.today() + timedelta(days=90)).isoformat()

    create_resp = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Phone Upgrade", "target_amount": "40000.00", "target_date": future_date},
    )
    goal_id = create_resp.json()["id"]

    # Deposit exactly 40,000
    dep_resp = await async_client.post(
        f"/goals/{goal_id}/contributions",
        headers=headers,
        json={"amount": "40000.00"},
    )
    assert dep_resp.status_code == 200
    goal = dep_resp.json()
    assert goal["status"] == "achieved"
    assert Decimal(goal["progress"]["left"]) == Decimal("0.00")
    assert goal["progress"]["pct"] == 100
    assert goal["progress"]["pill"] == "Done"
    assert goal["progress"]["status"] == "done"

    # Over-saving keeps left at zero rather than going negative
    over = await async_client.post(
        f"/goals/{goal_id}/contributions", headers=headers, json={"amount": "500.00"}
    )
    assert Decimal(over.json()["progress"]["left"]) == Decimal("0.00")
    assert over.json()["progress"]["pct"] == 101


@pytest.mark.asyncio
async def test_04b_status_follows_target_changes(async_client: httpx.AsyncClient) -> None:
    """4b. Raising the target re-opens an achieved goal; achieved cannot be claimed early."""
    _, headers = await register_and_login(async_client, "Goal Status User")
    goal = await create_goal(
        async_client, headers, target_amount="10000.00", initial_amount="10000.00"
    )
    assert goal["status"] == "achieved"

    raised = await async_client.patch(
        f"/goals/{goal['id']}", headers=headers, json={"target_amount": "15000.00"}
    )
    assert raised.status_code == 200
    assert raised.json()["status"] == "in_progress"
    assert raised.json()["progress"]["pill"] != "Done"

    early = await async_client.patch(
        f"/goals/{goal['id']}", headers=headers, json={"status": "achieved"}
    )
    assert early.status_code == 400

    # Lowering the target back under the saved amount completes it again
    lowered = await async_client.patch(
        f"/goals/{goal['id']}", headers=headers, json={"target_amount": "8000.00"}
    )
    assert lowered.json()["status"] == "achieved"

    # Paused is the user's call and survives deposits
    paused = await async_client.patch(
        f"/goals/{goal['id']}",
        headers=headers,
        json={"status": "paused", "target_amount": "20000.00"},
    )
    assert paused.json()["status"] == "paused"
    deposit = await async_client.post(
        f"/goals/{goal['id']}/contributions", headers=headers, json={"amount": "12000.00"}
    )
    assert deposit.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_05_invalid_amounts(async_client: httpx.AsyncClient) -> None:
    """5. Test rejection of invalid amounts (zero, negative, bad inputs)."""
    _, headers = await register_and_login(async_client, "Goal User 5")
    future_date = (date.today() + timedelta(days=90)).isoformat()

    # Zero target amount
    r1 = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Invalid Zero", "target_amount": "0.00", "target_date": future_date},
    )
    assert r1.status_code == 422 or r1.status_code == 400

    # Negative target amount
    r2 = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Invalid Negative", "target_amount": "-500.00", "target_date": future_date},
    )
    assert r2.status_code == 422 or r2.status_code == 400

    # Negative initial amount
    r3 = await async_client.post(
        "/goals",
        headers=headers,
        json={
            "name": "Neg Initial",
            "target_amount": "1000.00",
            "target_date": future_date,
            "initial_amount": "-50.00",
        },
    )
    assert r3.status_code == 422 or r3.status_code == 400

    # Valid goal, invalid contribution amount
    r_valid = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Valid Goal", "target_amount": "1000.00", "target_date": future_date},
    )
    gid = r_valid.json()["id"]

    r_contrib_zero = await async_client.post(
        f"/goals/{gid}/contributions",
        headers=headers,
        json={"amount": "0.00"},
    )
    assert r_contrib_zero.status_code in [400, 422]

    r_contrib_neg = await async_client.post(
        f"/goals/{gid}/contributions",
        headers=headers,
        json={"amount": "-100.00"},
    )
    assert r_contrib_neg.status_code in [400, 422]

    # Sub-paisa precision and amounts too large for NUMERIC(15,2) are rejected, not a 500
    for bad in ("10.005", "99999999999999.00", "abc"):
        r_bad = await async_client.post(
            f"/goals/{gid}/contributions", headers=headers, json={"amount": bad}
        )
        assert r_bad.status_code == 422, bad
    r_huge_target = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Huge", "target_amount": "1e20", "target_date": future_date},
    )
    assert r_huge_target.status_code == 422

    # Nothing was saved by the rejected calls
    unchanged = await async_client.get(f"/goals/{gid}", headers=headers)
    assert Decimal(unchanged.json()["current_amount"]) == Decimal("0.00")
    assert unchanged.json()["contributions"] == []


@pytest.mark.asyncio
async def test_06_goal_ownership(async_client: httpx.AsyncClient) -> None:
    """6. Test strict cross-user isolation on Goals."""
    _, h1 = await register_and_login(async_client, "Goal Owner User")
    _, h2 = await register_and_login(async_client, "Goal Intruder User")
    future_date = (date.today() + timedelta(days=90)).isoformat()

    create_resp = await async_client.post(
        "/goals",
        headers=h1,
        json={
            "name": "Private Secret Goal",
            "target_amount": "50000.00",
            "target_date": future_date,
        },
    )
    goal_id = create_resp.json()["id"]

    # Intruder tries GET
    get_res = await async_client.get(f"/goals/{goal_id}", headers=h2)
    assert get_res.status_code == 404

    # Intruder tries PATCH
    patch_res = await async_client.patch(f"/goals/{goal_id}", headers=h2, json={"name": "Hacked"})
    assert patch_res.status_code == 404

    # Intruder tries DELETE
    del_res = await async_client.delete(f"/goals/{goal_id}", headers=h2)
    assert del_res.status_code == 404

    # Intruder tries adding money
    add_res = await async_client.post(
        f"/goals/{goal_id}/contributions", headers=h2, json={"amount": "1000.00"}
    )
    assert add_res.status_code == 404

    # Intruder sees nothing in list/totals
    assert (await async_client.get("/goals", headers=h2)).json() == []
    assert (await async_client.get("/goals/totals", headers=h2)).json()["count"] == 0

    # Unauthenticated access is refused
    assert (await async_client.get("/goals")).status_code == 401

    # Owner's goal is untouched
    owner_view = await async_client.get(f"/goals/{goal_id}", headers=h1)
    assert owner_view.json()["name"] == "Private Secret Goal"
    assert Decimal(owner_view.json()["current_amount"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_06b_goal_ownership_of_accounts_and_contributions(
    async_client: httpx.AsyncClient,
) -> None:
    """6b. A goal can't be funded from someone else's account, nor their contributions undone."""
    _, h1 = await register_and_login(async_client, "Goal Funds Owner")
    _, h2 = await register_and_login(async_client, "Goal Funds Intruder")
    foreign_acc = await create_account(async_client, h2, "Intruder Bank")
    goal = await create_goal(async_client, h1, target_amount="5000.00")

    with_foreign = await async_client.post(
        f"/goals/{goal['id']}/contributions",
        headers=h1,
        json={"amount": "100.00", "account_id": foreign_acc["id"]},
    )
    assert with_foreign.status_code == 404
    create_foreign = await async_client.post(
        "/goals",
        headers=h1,
        json={
            "name": "Seeded from foreign",
            "target_amount": "100.00",
            "target_date": "2027-01-01",
            "initial_amount": "50.00",
            "account_id": foreign_acc["id"],
        },
    )
    assert create_foreign.status_code == 404

    funded = await async_client.post(
        f"/goals/{goal['id']}/contributions", headers=h1, json={"amount": "100.00"}
    )
    contribution_id = funded.json()["contributions"][0]["id"]
    undo = await async_client.delete(
        f"/goals/{goal['id']}/contributions/{contribution_id}", headers=h2
    )
    assert undo.status_code == 404


@pytest.mark.asyncio
async def test_07_goal_update_and_delete(async_client: httpx.AsyncClient) -> None:
    """7. Test updating goal properties and deleting goals."""
    _, headers = await register_and_login(async_client, "Goal User 7")
    future_date = (date.today() + timedelta(days=60)).isoformat()

    resp = await async_client.post(
        "/goals",
        headers=headers,
        json={"name": "Initial Name", "target_amount": "20000.00", "target_date": future_date},
    )
    goal_id = resp.json()["id"]

    # Update name, target and deadline
    new_deadline = (date.today() + timedelta(days=400)).isoformat()
    patch_resp = await async_client.patch(
        f"/goals/{goal_id}",
        headers=headers,
        json={
            "name": "Updated Name",
            "target_amount": "25000.00",
            "icon": "star",
            "target_date": new_deadline,
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["name"] == "Updated Name"
    assert Decimal(updated["target_amount"]) == Decimal("25000.00")
    assert updated["icon"] == "star"
    assert updated["target_date"] == new_deadline

    # Delete goal (with a contribution, which must go with it)
    await async_client.post(
        f"/goals/{goal_id}/contributions", headers=headers, json={"amount": "1000.00"}
    )
    del_resp = await async_client.delete(f"/goals/{goal_id}", headers=headers)
    assert del_resp.status_code == 200

    # Verify 404 after deletion
    get_del = await async_client.get(f"/goals/{goal_id}", headers=headers)
    assert get_del.status_code == 404

    async with AsyncSessionLocal() as db:
        orphans = await db.scalar(
            select(func.count())
            .select_from(GoalContribution)
            .where(GoalContribution.goal_id == uuid.UUID(goal_id))
        )
    assert orphans == 0


@pytest.mark.asyncio
async def test_07b_undo_contribution(async_client: httpx.AsyncClient) -> None:
    """7b. Removing a contribution takes its amount off and re-opens a completed goal."""
    _, headers = await register_and_login(async_client, "Goal Undo User")
    goal = await create_goal(async_client, headers, target_amount="3000.00")

    await async_client.post(
        f"/goals/{goal['id']}/contributions", headers=headers, json={"amount": "1000.00"}
    )
    done = await async_client.post(
        f"/goals/{goal['id']}/contributions", headers=headers, json={"amount": "2000.00"}
    )
    assert done.json()["status"] == "achieved"
    last_id = done.json()["contributions"][0]["id"]

    undone = await async_client.delete(
        f"/goals/{goal['id']}/contributions/{last_id}", headers=headers
    )
    assert undone.status_code == 200
    body = undone.json()
    assert Decimal(body["current_amount"]) == Decimal("1000.00")
    assert body["status"] == "in_progress"
    assert len(body["contributions"]) == 1

    again = await async_client.delete(
        f"/goals/{goal['id']}/contributions/{last_id}", headers=headers
    )
    assert again.status_code == 404


@pytest.mark.asyncio
async def test_08_goals_totals_summary(async_client: httpx.AsyncClient) -> None:
    """8. Test aggregated goals totals."""
    _, headers = await register_and_login(async_client, "Goal User 8")
    future_date = (date.today() + timedelta(days=90)).isoformat()

    await async_client.post(
        "/goals",
        headers=headers,
        json={
            "name": "Goal A",
            "target_amount": "10000.00",
            "initial_amount": "4000.00",
            "target_date": future_date,
        },
    )
    await async_client.post(
        "/goals",
        headers=headers,
        json={
            "name": "Goal B",
            "target_amount": "20000.00",
            "initial_amount": "6000.00",
            "target_date": future_date,
        },
    )

    totals_resp = await async_client.get("/goals/totals", headers=headers)
    assert totals_resp.status_code == 200
    t = totals_resp.json()
    assert Decimal(t["total_saved"]) == Decimal("10000.00")
    assert Decimal(t["total_target"]) == Decimal("30000.00")
    assert Decimal(t["total_left"]) == Decimal("20000.00")
    assert t["count"] == 2

    # Same figures through the versioned API
    versioned = await async_client.get("/api/v1/goals/totals", headers=headers)
    assert versioned.status_code == 200
    assert Decimal(versioned.json()["total_saved"]) == Decimal("10000.00")


# ==============================================================================
# RECURRING PAYMENTS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_09_create_recurring_payment(async_client: httpx.AsyncClient) -> None:
    """9. Test creating recurring payments of various kinds."""
    _, headers = await register_and_login(async_client, "Recurring User 1")
    acc = await create_account(async_client, headers, "HDFC Salary Account", "80000.00")

    # 1. Recurring Bill (Rent)
    r1 = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Apartment Rent",
            "kind": "bill",
            "amount": "15000.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-11-01",
            "notes": "Monthly house rent",
        },
    )
    assert r1.status_code == 201
    rent = r1.json()
    assert rent["title"] == "Apartment Rent"
    assert rent["kind"] == "bill"
    assert Decimal(rent["amount"]) == Decimal("15000.00")
    assert rent["is_active"] is True
    assert rent["anchor_day"] == 1
    assert rent["auto_pay"] is False

    # 2. Subscription (Spotify)
    r2 = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Spotify Premium",
            "kind": "subscription",
            "amount": "119.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-11-05",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["kind"] == "subscription"

    # 3. Recurring Income (Salary)
    r3 = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Tech Consulting Retainer",
            "kind": "income",
            "amount": "45000.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-11-01",
        },
    )
    assert r3.status_code == 201
    assert r3.json()["kind"] == "income"

    # 4. Generic recurring expense
    r4 = await create_recurring(
        async_client, headers, acc["id"], title="Maid", kind="expense", frequency="weekly"
    )
    assert r4["kind"] == "expense"
    assert r4["frequency"] == "weekly"

    listed = await async_client.get("/recurring?month=2026-11", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 4
    assert len((await async_client.get("/recurring?kind=income", headers=headers)).json()) == 1


@pytest.mark.asyncio
async def test_09b_creating_recurring_books_nothing(async_client: httpx.AsyncClient) -> None:
    """9b. Even an auto-pay item that is already due creates no transaction until executed."""
    _, headers = await register_and_login(async_client, "Recurring No Side Effects")
    acc = await create_account(async_client, headers, "HDFC", "10000.00")
    await create_recurring(
        async_client,
        headers,
        acc["id"],
        auto_pay=True,
        next_due_date=(date.today() - timedelta(days=3)).isoformat(),
    )
    await async_client.get("/recurring", headers=headers)
    await async_client.get("/recurring/summary", headers=headers)

    assert await account_balance(async_client, headers, acc["id"]) == Decimal("10000.00")
    assert await list_transactions(async_client, headers) == []


@pytest.mark.asyncio
async def test_09c_invalid_recurring_input(async_client: httpx.AsyncClient) -> None:
    """9c. Bad frequency, kind, amount or month filter is rejected with 422."""
    _, headers = await register_and_login(async_client, "Recurring Validation")
    acc = await create_account(async_client, headers, "HDFC")
    base = {
        "title": "Bad",
        "account_id": acc["id"],
        "amount": "100.00",
        "next_due_date": "2026-11-01",
    }
    for override in (
        {"frequency": "hourly"},
        {"kind": "gift"},
        {"amount": "0.00"},
        {"amount": "-10.00"},
        {"amount": "1.234"},
        {"amount": "99999999999999.00"},
        {"title": ""},
    ):
        resp = await async_client.post("/recurring", headers=headers, json={**base, **override})
        assert resp.status_code == 422, override

    assert (await async_client.get("/recurring?month=2026-13", headers=headers)).status_code == 422
    assert (
        await async_client.get("/recurring/summary?month=Oct-2026", headers=headers)
    ).status_code == 422


@pytest.mark.asyncio
async def test_10_edit_recurring_payment(async_client: httpx.AsyncClient) -> None:
    """10. Test updating recurring payment fields."""
    _, headers = await register_and_login(async_client, "Recurring User 2")
    acc = await create_account(async_client, headers, "Primary Bank", "30000.00")

    create_resp = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Gym Membership",
            "kind": "bill",
            "amount": "2000.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-11-10",
            "notes": "Annual plan billed monthly",
        },
    )
    rec_id = create_resp.json()["id"]

    # Patch amount and title
    patch_resp = await async_client.patch(
        f"/recurring/{rec_id}",
        headers=headers,
        json={"title": "Gold's Gym Membership", "amount": "2500.00", "frequency": "quarterly"},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["title"] == "Gold's Gym Membership"
    assert Decimal(updated["amount"]) == Decimal("2500.00")
    assert updated["frequency"] == "quarterly"
    assert updated["notes"] == "Annual plan billed monthly"

    # Explicit null clears optional fields; null on a required field leaves it alone
    cleared = await async_client.patch(
        f"/recurring/{rec_id}", headers=headers, json={"notes": None, "title": None}
    )
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
    assert cleared.json()["title"] == "Gold's Gym Membership"

    # Invalid edits are rejected
    assert (
        await async_client.patch(f"/recurring/{rec_id}", headers=headers, json={"amount": "0"})
    ).status_code == 422
    assert (
        await async_client.patch(
            f"/recurring/{rec_id}", headers=headers, json={"frequency": "fortnightly"}
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_10b_new_due_date_resets_anchor(async_client: httpx.AsyncClient) -> None:
    """10b. Moving the due date re-pins the schedule to the new day of month."""
    _, headers = await register_and_login(async_client, "Recurring Anchor Edit")
    acc = await create_account(async_client, headers, "HDFC", "10000.00")
    rec = await create_recurring(async_client, headers, acc["id"], next_due_date="2027-01-31")
    assert rec["anchor_day"] == 31

    moved = await async_client.patch(
        f"/recurring/{rec['id']}", headers=headers, json={"next_due_date": "2027-02-15"}
    )
    assert moved.json()["anchor_day"] == 15
    paid = await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
    assert paid.json()["new_due_date"] == "2027-03-15"


@pytest.mark.asyncio
async def test_11_deactivate_and_activate(async_client: httpx.AsyncClient) -> None:
    """11. Test deactivating and reactivating recurring payments."""
    _, headers = await register_and_login(async_client, "Recurring User 3")
    acc = await create_account(async_client, headers, "Bank Account", "10000.00")
    upcoming = date.today() + timedelta(days=30)

    resp = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Newspaper Subscription",
            "kind": "subscription",
            "amount": "300.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": upcoming.isoformat(),
        },
    )
    rec_id = resp.json()["id"]
    assert resp.json()["is_active"] is True

    # Deactivate
    deact_resp = await async_client.post(f"/recurring/{rec_id}/deactivate", headers=headers)
    assert deact_resp.status_code == 200
    assert deact_resp.json()["status"] == "inactive"
    assert deact_resp.json()["is_active"] is False

    # Inactive payments can't be executed and drop out of the summary
    blocked = await async_client.post(f"/recurring/{rec_id}/trigger", headers=headers)
    assert blocked.status_code == 400
    summary = (
        await async_client.get(f"/recurring/summary?month={upcoming:%Y-%m}", headers=headers)
    ).json()
    assert summary["outgoing_count"] == 0
    assert summary["subscriptions_count"] == 0
    assert len((await async_client.get("/recurring?status=inactive", headers=headers)).json()) == 1

    # Reactivate (future due date is kept as is)
    act_resp = await async_client.post(f"/recurring/{rec_id}/activate", headers=headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "active"
    assert act_resp.json()["is_active"] is True
    assert act_resp.json()["next_due_date"] == upcoming.isoformat()
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("10000.00")


@pytest.mark.asyncio
async def test_11b_reactivation_skips_missed_occurrences(async_client: httpx.AsyncClient) -> None:
    """11b. Switching a payment back on resumes from today instead of back-filling."""
    _, headers = await register_and_login(async_client, "Recurring Resume User")
    acc = await create_account(async_client, headers, "HDFC", "10000.00")
    today = date.today()
    stale_due = today - timedelta(days=75)

    endpoint_rec = await create_recurring(
        async_client, headers, acc["id"], next_due_date=stale_due.isoformat(), status="paused"
    )
    patch_rec = await create_recurring(
        async_client, headers, acc["id"], next_due_date=stale_due.isoformat(), status="inactive"
    )

    resumed = (
        await async_client.post(f"/recurring/{endpoint_rec['id']}/activate", headers=headers)
    ).json()
    patched = (
        await async_client.patch(
            f"/recurring/{patch_rec['id']}", headers=headers, json={"status": "active"}
        )
    ).json()

    for rec in (resumed, patched):
        next_due = date.fromisoformat(rec["next_due_date"])
        assert today <= next_due < today + timedelta(days=32)
        # Still on the original schedule's day of month
        assert rec["anchor_day"] == stale_due.day
        month_len = calendar.monthrange(next_due.year, next_due.month)[1]
        assert next_due.day == min(stale_due.day, month_len)

    # And nothing is due for the auto-pay job to back-fill
    batch = await async_client.post(
        "/recurring/process-due?auto_pay_only=false&dry_run=true", headers=headers
    )
    assert all(r["previous_due_date"] >= today.isoformat() for r in batch.json()["results"])
    assert await list_transactions(async_client, headers) == []


def test_12_frequency_and_date_calculations() -> None:
    """12. Test next occurrence date calculation for all cadences."""
    base = date(2026, 1, 15)
    # Daily
    assert calculate_next_occurrence(base, "daily") == date(2026, 1, 16)
    assert calculate_next_occurrence(date(2026, 12, 31), "daily") == date(2027, 1, 1)
    # Weekly
    assert calculate_next_occurrence(base, "weekly") == date(2026, 1, 22)
    assert calculate_next_occurrence(date(2028, 2, 26), "weekly") == date(2028, 3, 4)
    # Monthly
    assert calculate_next_occurrence(base, "monthly") == date(2026, 2, 15)
    assert calculate_next_occurrence(date(2026, 12, 15), "monthly") == date(2027, 1, 15)
    # Month end clipping (Jan 31 -> Feb 28)
    assert calculate_next_occurrence(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
    # Quarterly
    assert calculate_next_occurrence(base, "quarterly") == date(2026, 4, 15)
    assert calculate_next_occurrence(date(2026, 11, 15), "quarterly") == date(2027, 2, 15)
    # Yearly
    assert calculate_next_occurrence(base, "yearly") == date(2027, 1, 15)

    with pytest.raises(ValueError):
        calculate_next_occurrence(base, "fortnightly")


def test_12b_month_end_schedules_do_not_drift() -> None:
    """12b. A schedule pinned to the 31st/30th/29th returns to it after a short month."""
    due, seen = date(2027, 1, 31), []
    for _ in range(5):
        due = calculate_next_occurrence(due, "monthly", anchor_day=31)
        seen.append(due)
    assert seen == [
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
        date(2027, 5, 31),
        date(2027, 6, 30),
    ]

    assert calculate_next_occurrence(date(2026, 11, 30), "quarterly", 30) == date(2027, 2, 28)
    assert calculate_next_occurrence(date(2027, 2, 28), "quarterly", 30) == date(2027, 5, 30)

    # Leap day: Feb 29 -> Feb 28 in common years -> Feb 29 again in the next leap year
    yearly, years = date(2028, 2, 29), []
    for _ in range(4):
        yearly = calculate_next_occurrence(yearly, "yearly", anchor_day=29)
        years.append(yearly)
    assert years == [date(2029, 2, 28), date(2030, 2, 28), date(2031, 2, 28), date(2032, 2, 29)]

    # A stored anchor that no longer matches the due date (edited elsewhere) is ignored
    assert effective_anchor_day(date(2027, 2, 28), 31) == 31
    assert effective_anchor_day(date(2027, 3, 15), 31) == 15
    assert effective_anchor_day(date(2027, 3, 15), None) == 15


@pytest.mark.asyncio
async def test_12c_execution_follows_frequency(async_client: httpx.AsyncClient) -> None:
    """12c. Executing an occurrence advances the due date by the payment's own cadence."""
    _, headers = await register_and_login(async_client, "Recurring Cadence User")
    acc = await create_account(async_client, headers, "HDFC", "100000.00")
    expected = {
        "daily": "2027-01-01",
        "weekly": "2027-01-07",
        "monthly": "2027-01-31",
        "quarterly": "2027-03-31",
        "yearly": "2027-12-31",
    }
    for frequency, next_due in expected.items():
        rec = await create_recurring(
            async_client, headers, acc["id"], frequency=frequency, next_due_date="2026-12-31"
        )
        paid = await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
        assert paid.status_code == 200
        assert paid.json()["new_due_date"] == next_due, frequency

    # Month-end bill through the API: Jan 31 -> Feb 28 -> Mar 31
    month_end = await create_recurring(async_client, headers, acc["id"], next_due_date="2027-01-31")
    first = await async_client.post(f"/recurring/{month_end['id']}/trigger", headers=headers)
    second = await async_client.post(f"/recurring/{month_end['id']}/trigger", headers=headers)
    assert first.json()["new_due_date"] == "2027-02-28"
    assert second.json()["new_due_date"] == "2027-03-31"


@pytest.mark.asyncio
async def test_13_recurring_ownership(async_client: httpx.AsyncClient) -> None:
    """13. Test recurring payment ownership isolation."""
    _, h1 = await register_and_login(async_client, "Rec Owner")
    _, h2 = await register_and_login(async_client, "Rec Intruder")
    acc = await create_account(async_client, h1, "Owner Bank", "5000.00")

    resp = await async_client.post(
        "/recurring",
        headers=h1,
        json={
            "title": "Private Bill",
            "kind": "bill",
            "amount": "1000.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-11-01",
        },
    )
    rec_id = resp.json()["id"]

    assert (await async_client.get(f"/recurring/{rec_id}", headers=h2)).status_code == 404
    assert (
        await async_client.patch(f"/recurring/{rec_id}", headers=h2, json={"amount": "50.00"})
    ).status_code == 404
    assert (await async_client.delete(f"/recurring/{rec_id}", headers=h2)).status_code == 404
    assert (await async_client.post(f"/recurring/{rec_id}/trigger", headers=h2)).status_code == 404
    for action in ("deactivate", "activate"):
        assert (
            await async_client.post(f"/recurring/{rec_id}/{action}", headers=h2)
        ).status_code == 404
    assert (await async_client.get("/recurring", headers=h2)).json() == []
    intruder_batch = await async_client.post(
        "/recurring/process-due?auto_pay_only=false", headers=h2
    )
    assert intruder_batch.json()["processed_count"] == 0

    # Owner's payment and account are untouched
    owner_view = (await async_client.get(f"/recurring/{rec_id}", headers=h1)).json()
    assert Decimal(owner_view["amount"]) == Decimal("1000.00")
    assert owner_view["status"] == "active"
    assert await account_balance(async_client, h1, acc["id"]) == Decimal("5000.00")


@pytest.mark.asyncio
async def test_13b_recurring_rejects_foreign_accounts_and_categories(
    async_client: httpx.AsyncClient,
) -> None:
    """13b. A recurring payment can't point at another user's account or custom category."""
    _, h1 = await register_and_login(async_client, "Rec Link Owner")
    _, h2 = await register_and_login(async_client, "Rec Link Intruder")
    own_acc = await create_account(async_client, h1, "Own Bank")
    foreign_acc = await create_account(async_client, h2, "Foreign Bank")
    foreign_cat = await async_client.post(
        "/categories", headers=h2, json={"name": "Secret", "category_type": "expense"}
    )
    assert foreign_cat.status_code == 201

    on_foreign_acc = await async_client.post(
        "/recurring",
        headers=h1,
        json={
            "title": "Sneaky",
            "amount": "10.00",
            "account_id": foreign_acc["id"],
            "next_due_date": "2026-11-01",
        },
    )
    assert on_foreign_acc.status_code == 404
    on_foreign_cat = await async_client.post(
        "/recurring",
        headers=h1,
        json={
            "title": "Sneaky",
            "amount": "10.00",
            "account_id": own_acc["id"],
            "category_id": foreign_cat.json()["id"],
            "next_due_date": "2026-11-01",
        },
    )
    assert on_foreign_cat.status_code == 404

    rec = await create_recurring(async_client, h1, own_acc["id"])
    move = await async_client.patch(
        f"/recurring/{rec['id']}", headers=h1, json={"account_id": foreign_acc["id"]}
    )
    assert move.status_code == 404
    assert await account_balance(async_client, h2, foreign_acc["id"]) == Decimal("50000.00")


@pytest.mark.asyncio
async def test_14_safe_recurring_execution_architecture(async_client: httpx.AsyncClient) -> None:
    """14. Test safe execution architecture (dry run vs explicit commit with balance update)."""
    _, headers = await register_and_login(async_client, "Execution User")
    acc = await create_account(async_client, headers, "HDFC Main", "10000.00")

    # Create monthly internet bill of ₹1,000
    create_resp = await async_client.post(
        "/recurring",
        headers=headers,
        json={
            "title": "Airtel Fiber",
            "kind": "bill",
            "amount": "1000.00",
            "account_id": acc["id"],
            "frequency": "monthly",
            "next_due_date": "2026-10-05",
        },
    )
    rec_id = create_resp.json()["id"]

    # 1. Dry run execution: does NOT touch account balance or database state
    dry_resp = await async_client.post(
        f"/recurring/{rec_id}/trigger",
        headers=headers,
        json={"dry_run": True},
    )
    assert dry_resp.status_code == 200
    assert dry_resp.json()["dry_run"] is True
    assert dry_resp.json()["transaction_id"] is None
    assert dry_resp.json()["new_due_date"] == "2026-11-05"

    # Verify account balance and schedule untouched
    acc_check1 = await async_client.get(f"/accounts/{acc['id']}", headers=headers)
    assert Decimal(acc_check1.json()["balance"]) == Decimal("10000.00")
    still_due = await async_client.get(f"/recurring/{rec_id}", headers=headers)
    assert still_due.json()["next_due_date"] == "2026-10-05"
    assert await list_transactions(async_client, headers) == []

    # 2. Real execution: creates transaction and deducts balance
    real_resp = await async_client.post(
        f"/recurring/{rec_id}/trigger",
        headers=headers,
        json={"dry_run": False, "expected_due_date": "2026-10-05"},
    )
    assert real_resp.status_code == 200
    real_res = real_resp.json()
    assert real_res["dry_run"] is False
    assert real_res["transaction_id"] is not None
    assert real_res["new_due_date"] == "2026-11-05"

    # Verify balance decreased by 1,000 to 9,000
    acc_check2 = await async_client.get(f"/accounts/{acc['id']}", headers=headers)
    assert Decimal(acc_check2.json()["balance"]) == Decimal("9000.00")

    # Verify real transaction was logged with is_recurring=True, dated on the occurrence
    tx_check = await async_client.get(
        f"/transactions/{real_res['transaction_id']}", headers=headers
    )
    assert tx_check.status_code == 200
    tx_data = tx_check.json()
    assert tx_data["is_recurring"] is True
    assert tx_data["transaction_type"] == "expense"
    assert Decimal(tx_data["amount"]) == Decimal("1000.00")
    assert tx_data["transaction_date"].startswith("2026-10-05")

    # 3. A retry of the same occurrence is refused, not booked twice
    retry = await async_client.post(
        f"/recurring/{rec_id}/trigger",
        headers=headers,
        json={"expected_due_date": "2026-10-05"},
    )
    assert retry.status_code == 409
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("9000.00")
    assert len(await list_transactions(async_client, headers)) == 1
    paid = (await async_client.get(f"/recurring/{rec_id}", headers=headers)).json()
    assert paid["last_paid_at"] is not None


@pytest.mark.asyncio
async def test_14a_parallel_triggers_book_one_occurrence(async_client: httpx.AsyncClient) -> None:
    """14a. Several simultaneous triggers for the same occurrence book it exactly once."""
    _, headers = await register_and_login(async_client, "Execution Race User")
    acc = await create_account(async_client, headers, "HDFC", "10000.00")
    rec = await create_recurring(async_client, headers, acc["id"], next_due_date="2026-12-05")

    responses = await asyncio.gather(
        *(
            async_client.post(
                f"/recurring/{rec['id']}/trigger",
                headers=headers,
                json={"expected_due_date": "2026-12-05"},
            )
            for _ in range(5)
        )
    )
    assert sorted(r.status_code for r in responses) == [200, 409, 409, 409, 409]
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("9000.00")
    assert len(await list_transactions(async_client, headers)) == 1
    after = (await async_client.get(f"/recurring/{rec['id']}", headers=headers)).json()
    assert after["next_due_date"] == "2027-01-05"


@pytest.mark.asyncio
async def test_14b_recurring_income_credits_account(async_client: httpx.AsyncClient) -> None:
    """14b. Executing recurring income books an income transaction and credits the account."""
    _, headers = await register_and_login(async_client, "Execution Income User")
    acc = await create_account(async_client, headers, "Salary A/c", "1000.00")
    rec = await create_recurring(
        async_client, headers, acc["id"], title="Salary", kind="income", amount="35000.00"
    )
    paid = await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
    assert paid.status_code == 200
    tx = (
        await async_client.get(f"/transactions/{paid.json()['transaction_id']}", headers=headers)
    ).json()
    assert tx["transaction_type"] == "income"
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("36000.00")


@pytest.mark.asyncio
async def test_14c_emi_progress_and_completion(async_client: httpx.AsyncClient) -> None:
    """14c. Each EMI instalment updates paid/remaining exactly; the last one closes the EMI."""
    _, headers = await register_and_login(async_client, "Execution EMI User")
    acc = await create_account(async_client, headers, "HDFC", "20000.00")
    rec = await create_recurring(
        async_client,
        headers,
        acc["id"],
        title="Bike loan EMI",
        kind="emi",
        amount="3200.00",
        metadata_json={"emi": {"paid": 22, "total": 24, "remaining": 6400}, "letter": "B"},
    )

    await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
    after_one = (await async_client.get(f"/recurring/{rec['id']}", headers=headers)).json()
    assert after_one["metadata_json"]["emi"] == {"paid": 23, "total": 24, "remaining": "3200.00"}
    assert after_one["metadata_json"]["letter"] == "B"
    assert after_one["status"] == "active"

    await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
    after_last = (await async_client.get(f"/recurring/{rec['id']}", headers=headers)).json()
    assert after_last["metadata_json"]["emi"]["paid"] == 24
    assert after_last["metadata_json"]["emi"]["remaining"] == "0.00"
    assert after_last["status"] == "inactive"

    assert (
        await async_client.post(f"/recurring/{rec['id']}/trigger", headers=headers)
    ).status_code == 400
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("13600.00")


@pytest.mark.asyncio
async def test_15_batch_due_payments_processor(async_client: httpx.AsyncClient) -> None:
    """15. Background batch: only auto-pay items, dated on their due date, idempotent re-runs."""
    _, headers = await register_and_login(async_client, "Batch User")
    acc = await create_account(async_client, headers, "Savings", "50000.00")

    # Past due bills (due yesterday): one opted into auto-pay, one not
    yesterday = date.today() - timedelta(days=1)
    auto = await create_recurring(
        async_client,
        headers,
        acc["id"],
        title="Electricity Due",
        amount="500.00",
        next_due_date=yesterday.isoformat(),
        auto_pay=True,
    )
    manual = await create_recurring(
        async_client,
        headers,
        acc["id"],
        title="Plumber",
        amount="300.00",
        next_due_date=yesterday.isoformat(),
    )
    # Not yet due
    await create_recurring(
        async_client,
        headers,
        acc["id"],
        title="Future",
        next_due_date=(date.today() + timedelta(days=5)).isoformat(),
        auto_pay=True,
    )

    # Dry run reports what would happen and changes nothing
    dry = (await async_client.post("/recurring/process-due?dry_run=true", headers=headers)).json()
    assert dry["dry_run"] is True
    assert dry["executed_count"] == 1
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("50000.00")

    batch_resp = await async_client.post(
        "/recurring/process-due?dry_run=false",
        headers=headers,
    )
    assert batch_resp.status_code == 200
    data = batch_resp.json()
    assert data["processed_count"] == 1
    assert data["executed_count"] == 1
    assert data["failed_count"] == 0
    result = data["results"][0]
    assert result["recurring_payment_id"] == auto["id"]
    assert result["execution_date"] == yesterday.isoformat()
    tx = (
        await async_client.get(f"/transactions/{result['transaction_id']}", headers=headers)
    ).json()
    assert tx["transaction_date"].startswith(yesterday.isoformat())
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("49500.00")

    # Running the job again the same day books nothing new
    rerun = (await async_client.post("/recurring/process-due", headers=headers)).json()
    assert rerun["processed_count"] == 0
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("49500.00")

    # The manual bill is still waiting for an explicit trigger
    manual_now = (await async_client.get(f"/recurring/{manual['id']}", headers=headers)).json()
    assert manual_now["next_due_date"] == yesterday.isoformat()
    assert len(await list_transactions(async_client, headers)) == 1

    # ...which the user can give explicitly
    explicit = (
        await async_client.post("/recurring/process-due?auto_pay_only=false", headers=headers)
    ).json()
    assert [r["recurring_payment_id"] for r in explicit["results"]] == [manual["id"]]
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("49200.00")


@pytest.mark.asyncio
async def test_15b_batch_isolates_failures_and_skips_processed(
    async_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """15b. One payment failing or already processed elsewhere doesn't stop the batch."""
    user, headers = await register_and_login(async_client, "Batch Isolation User")
    acc = await create_account(async_client, headers, "Savings", "10000.00")
    due = date.today() - timedelta(days=2)
    titles = ["Already done", "Explodes", "Healthy"]
    recs = {}
    for offset, title in enumerate(titles):
        recs[title] = await create_recurring(
            async_client,
            headers,
            acc["id"],
            title=title,
            amount="100.00",
            next_due_date=(due + timedelta(days=offset)).isoformat(),
            auto_pay=True,
        )

    real_execute = RecurringService.execute_payment

    async def flaky_execute(**kwargs: object) -> object:
        if kwargs["payment_id"] == uuid.UUID(recs["Already done"]["id"]):
            raise HTTPException(status_code=409, detail="already processed")
        if kwargs["payment_id"] == uuid.UUID(recs["Explodes"]["id"]):
            # A real database error: leaves the session's transaction aborted
            await kwargs["db"].execute(text("SELECT 1/0"))  # type: ignore[attr-defined]
        return await real_execute(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(RecurringService, "execute_payment", staticmethod(flaky_execute))

    async with AsyncSessionLocal() as db:
        outcome = await RecurringService.process_due_payments(db, user_id=uuid.UUID(user["id"]))

    assert outcome.processed_count == 3
    assert (outcome.skipped_count, outcome.failed_count, outcome.executed_count) == (1, 1, 1)
    by_title = {r.title: r.status for r in outcome.results}
    assert by_title == {
        "Already done": "skipped: already processed",
        "Explodes": "error: internal error",
        "Healthy": "executed",
    }
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("9900.00")


@pytest.mark.asyncio
async def test_15c_batch_does_not_overwrite_concurrent_balance_changes(
    async_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """15c. Between two payments on one account, another request moves the balance; the batch
    must re-read it under lock rather than write back a copy its session already holds."""
    user, headers = await register_and_login(async_client, "Batch Stale Balance User")
    acc = await create_account(async_client, headers, "Shared", "10000.00")
    due = date.today() - timedelta(days=1)
    for title in ("First", "Second"):
        await create_recurring(
            async_client,
            headers,
            acc["id"],
            title=title,
            amount="100.00",
            next_due_date=due.isoformat(),
            auto_pay=True,
        )

    real_execute = RecurringService.execute_payment
    cached: list[Account] = []

    async def execute_then_deposit_elsewhere(**kwargs: object) -> object:
        result = await real_execute(**kwargs)  # type: ignore[arg-type]
        if not cached:
            # The batch session now has the account cached at ₹9,900 ...
            batch_db = kwargs["db"]
            cached.append(await batch_db.get(Account, uuid.UUID(acc["id"])))  # type: ignore[attr-defined]
            # ... while another request deposits ₹1,000
            async with AsyncSessionLocal() as other:
                await other.execute(
                    update(Account)
                    .where(Account.id == uuid.UUID(acc["id"]))
                    .values(balance=Account.balance + 1000)
                )
                await other.commit()
        return result

    monkeypatch.setattr(
        RecurringService, "execute_payment", staticmethod(execute_then_deposit_elsewhere)
    )

    async with AsyncSessionLocal() as db:
        outcome = await RecurringService.process_due_payments(db, user_id=uuid.UUID(user["id"]))

    assert outcome.executed_count == 2
    assert await account_balance(async_client, headers, acc["id"]) == Decimal("10800.00")


# ==============================================================================
# DHAN INVARIANTS VERIFICATION
# ==============================================================================


@pytest.mark.asyncio
async def test_16_dhan_core_invariants_goals(async_client: httpx.AsyncClient) -> None:
    """16. Verify DHAN Core Invariants for Goals (Spec §6), as of the spec's 2026-09-30.

    MacBook: Target ₹1,20,000, 38%, ₹12,500/mo
    Emergency Fund: Target ₹2,00,000, Behind
    Kerala Trip: Target ₹30,000, 60%, On track
    TOTAL GOALS SAVED = ₹98,000
    TOTAL GOALS LEFT = ₹2,52,000
    Adding ₹12,500 to MacBook moves it to 48% and ₹10,417/mo
    """
    _, headers = await register_and_login(async_client, "DHAN Goals Invariant User")
    hdfc = await create_account(async_client, headers, "HDFC Bank", "200000.00")
    sbi = await create_account(async_client, headers, "SBI Savings", "200000.00")

    seed = [
        # name, target, deadline, icon, created, contributions (amount, account, date)
        (
            "MacBook",
            "120000.00",
            "2027-03-31",
            "laptop",
            "2026-07-01",
            [
                ("20000.00", sbi, "2026-07-15"),
                ("15000.00", hdfc, "2026-08-15"),
                ("10000.00", hdfc, "2026-09-15"),
            ],
        ),
        (
            "Emergency Fund",
            "200000.00",
            "2027-12-31",
            "shield",
            "2026-01-01",
            [
                ("10000.00", sbi, "2026-01-10"),
                ("10000.00", sbi, "2026-03-10"),
                ("15000.00", sbi, "2026-06-10"),
            ],
        ),
        (
            "Kerala Trip",
            "30000.00",
            "2026-12-15",
            "plane",
            "2026-07-01",
            [("10000.00", hdfc, "2026-07-20"), ("8000.00", hdfc, "2026-09-02")],
        ),
    ]
    ids = {}
    for name, target, deadline, icon, created, contributions in seed:
        goal = await create_goal(
            async_client,
            headers,
            name=name,
            target_amount=target,
            target_date=deadline,
            icon=icon,
            created_at=f"{created}T00:00:00Z",
        )
        ids[name] = goal["id"]
        for amount, account, when in contributions:
            resp = await async_client.post(
                f"/goals/{goal['id']}/contributions",
                headers=headers,
                json={"amount": amount, "account_id": account["id"], "date": when},
            )
            assert resp.status_code == 200

    # -------------------------------------------------------------------------
    # VERIFY TOTAL INVARIANTS: ₹98,000 saved across 3 goals, ₹2,52,000 to go
    # -------------------------------------------------------------------------
    totals_resp = await async_client.get(f"/goals/totals?as_of={SPEC_TODAY}", headers=headers)
    assert totals_resp.status_code == 200
    totals = totals_resp.json()

    assert Decimal(totals["total_saved"]) == Decimal("98000.00"), (
        f"Expected ₹98,000 saved, got {totals['total_saved']}"
    )
    assert Decimal(totals["total_left"]) == Decimal("252000.00"), (
        f"Expected ₹2,52,000 left, got {totals['total_left']}"
    )
    assert Decimal(totals["total_target"]) == Decimal("350000.00")
    assert totals["count"] == 3

    # Check MacBook individual metrics
    mac_get = await async_client.get(f"/goals/{ids['MacBook']}?as_of={SPEC_TODAY}", headers=headers)
    assert mac_get.status_code == 200
    mac_data = mac_get.json()
    assert Decimal(mac_data["current_amount"]) == Decimal("45000.00")
    assert mac_data["progress"]["pct"] == 38  # 45,000 / 120,000 = 37.5% -> 38%
    assert mac_data["progress"]["months_left"] == 6
    assert Decimal(mac_data["progress"]["monthly"]) == Decimal("12500")
    assert mac_data["progress"]["pill"] == "₹12,500/mo"

    # Check Emergency Fund individual metrics
    em_get = await async_client.get(
        f"/goals/{ids['Emergency Fund']}?as_of={SPEC_TODAY}", headers=headers
    )
    assert em_get.status_code == 200
    assert Decimal(em_get.json()["current_amount"]) == Decimal("35000.00")
    assert em_get.json()["progress"]["status"] == "behind"
    assert em_get.json()["progress"]["pill"] == "Behind"

    # Check Kerala Trip individual metrics
    ker_get = await async_client.get(
        f"/goals/{ids['Kerala Trip']}?as_of={SPEC_TODAY}", headers=headers
    )
    assert ker_get.status_code == 200
    ker_data = ker_get.json()
    assert Decimal(ker_data["current_amount"]) == Decimal("18000.00")
    assert ker_data["progress"]["pct"] == 60  # 18,000 / 30,000 = 60%
    assert ker_data["progress"]["pill"] == "On track"

    # Add ₹12,500 to MacBook: moves it to 48% and ₹10,417 a month
    add_resp = await async_client.post(
        f"/goals/{ids['MacBook']}/contributions",
        headers=headers,
        json={"amount": "12500.00", "account_id": hdfc["id"], "date": SPEC_TODAY},
    )
    assert add_resp.status_code == 200
    assert Decimal(add_resp.json()["current_amount"]) == Decimal("57500.00")
    mac_after = (
        await async_client.get(f"/goals/{ids['MacBook']}?as_of={SPEC_TODAY}", headers=headers)
    ).json()
    assert mac_after["progress"]["pct"] == 48  # 57,500 / 120,000 = 47.9% -> 48%
    assert Decimal(mac_after["progress"]["monthly"]) == Decimal("10417")  # 62,500 / 6

    # Totals move with it; account balances never did
    after_totals = (
        await async_client.get(f"/goals/totals?as_of={SPEC_TODAY}", headers=headers)
    ).json()
    assert Decimal(after_totals["total_saved"]) == Decimal("110500.00")
    assert await account_balance(async_client, headers, hdfc["id"]) == Decimal("200000.00")


@pytest.mark.asyncio
async def test_17_dhan_core_invariants_recurring(async_client: httpx.AsyncClient) -> None:
    """17. Verify DHAN Core Invariants for Recurring Payments & Subscriptions (Spec §6).

    October outgoing: ₹14,391 across 9 payments
    Next 7 days (from 2026-09-30): ₹8,499; later this month: ChatGPT Plus, Bike loan EMI
    Subscriptions: ₹2,692/month, ₹32,304/year across 5 subscriptions
    """
    _, headers = await register_and_login(async_client, "DHAN Recurring Invariant User")
    hdfc = await create_account(async_client, headers, "HDFC Bank", "100000.00")
    icici = await create_account(async_client, headers, "ICICI Card", "50000.00")

    # Seed recurring payments matching mock/seed.ts: (title, kind, amount, account, next due)
    items = [
        ("Rent", "bill", "6000.00", hdfc, "2026-10-01"),
        ("Internet", "bill", "999.00", hdfc, "2026-10-05"),
        ("Gym membership", "bill", "1500.00", hdfc, "2026-10-07"),
        ("ChatGPT Plus", "subscription", "1700.00", icici, "2026-10-12"),
        ("Bike loan EMI", "emi", "3200.00", hdfc, "2026-10-15"),
        ("Netflix", "subscription", "649.00", icici, "2026-10-18"),
        ("YouTube Premium", "subscription", "149.00", hdfc, "2026-10-21"),
        ("Spotify", "subscription", "119.00", hdfc, "2026-10-25"),
        ("iCloud+", "subscription", "75.00", hdfc, "2026-10-28"),
        ("Salary", "income", "35000.00", hdfc, "2026-10-01"),
    ]
    for title, kind, amount, account, next_due in items:
        await create_recurring(
            async_client,
            headers,
            account["id"],
            title=title,
            kind=kind,
            amount=amount,
            next_due_date=next_due,
        )

    # Fetch summary for 2026-10
    sum_resp = await async_client.get(
        f"/recurring/summary?month=2026-10&as_of={SPEC_TODAY}", headers=headers
    )
    assert sum_resp.status_code == 200
    summary = sum_resp.json()

    # 1. October outgoing ₹14,391 across 9 payments
    assert Decimal(summary["outgoing_total"]) == Decimal("14391.00"), (
        f"Expected 14,391, got {summary['outgoing_total']}"
    )
    assert summary["outgoing_count"] == 9
    assert Decimal(summary["incoming_total"]) == Decimal("35000.00")
    assert summary["incoming_count"] == 1

    # 2. Next 7 days ₹8,499 (Rent, Internet, Gym); later list shows bills and big subscriptions
    assert Decimal(summary["upcoming_soon_total"]) == Decimal("8499.00")
    assert [r["title"] for r in summary["upcoming_soon"]] == ["Rent", "Internet", "Gym membership"]
    assert [r["title"] for r in summary["upcoming_later"]] == ["ChatGPT Plus", "Bike loan EMI"]

    # 3. Subscriptions ₹2,692 a month, ₹32,304 a year across 5 subscriptions
    # (1700 + 649 + 149 + 119 + 75 = 2692)
    assert Decimal(summary["subscriptions_monthly"]) == Decimal("2692.00")
    assert Decimal(summary["subscriptions_yearly"]) == Decimal("32304.00")
    assert summary["subscriptions_count"] == 5


@pytest.mark.asyncio
async def test_18_subscriptions_normalised_by_frequency(async_client: httpx.AsyncClient) -> None:
    """18. Non-monthly subscriptions count at their monthly cost; inactive ones don't count."""
    _, headers = await register_and_login(async_client, "Subscription Mix User")
    acc = await create_account(async_client, headers, "Card")
    for amount, frequency, sub_status in (
        ("100.00", "monthly", "active"),
        ("1200.00", "yearly", "active"),
        ("300.00", "quarterly", "active"),
        ("500.00", "monthly", "inactive"),
    ):
        await create_recurring(
            async_client,
            headers,
            acc["id"],
            kind="subscription",
            amount=amount,
            frequency=frequency,
            status=sub_status,
        )

    summary = (await async_client.get("/recurring/summary", headers=headers)).json()
    assert summary["subscriptions_count"] == 3
    assert Decimal(summary["subscriptions_monthly"]) == Decimal("300.00")  # 100 + 100 + 100
    assert Decimal(summary["subscriptions_yearly"]) == Decimal("3600.00")
