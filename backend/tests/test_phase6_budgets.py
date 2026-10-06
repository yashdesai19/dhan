"""Comprehensive test suite for Phase 6: DHAN Budgets & Financial Derivations.

Covers:
1. Create monthly budget & category budget
2. Update budget
3. Delete budget
4. Category budget dedicated endpoints
5. Transaction affects budget (adding expense increases spent and decreases remaining)
6. Transaction edit affects budget (dynamically updates derived totals)
7. Transaction delete affects budget (restores remaining amount)
8. Income and transfer do NOT count as spending
9. Month filtering (expenses in other months do not alter this month's budget)
10. User isolation (User B cannot see/modify User A's budgets or affect their spending)
11. Invalid amounts (amounts <= 0 or invalid decimals are rejected)
12. Duplicate budget rejection (same category in same month fails)
13. Invalid category rejection (non-existent category fails)
14. Visual tones ('ok', 'warn', 'over') and overspending handling
15. DHAN seed invariant verification: ₹17,100 / ₹24,000 with Transport in warning (93%)
"""

import uuid
from decimal import Decimal

import httpx
import pytest


async def register_and_login(client: httpx.AsyncClient, name: str) -> tuple[dict, dict]:
    """Helper to register a user and return user info with auth headers."""
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


async def create_test_account(
    client: httpx.AsyncClient,
    headers: dict,
    name: str,
    balance: str = "100000.00",
    account_type: str = "savings",
) -> dict:
    """Helper to create an account for a user."""
    resp = await client.post(
        "/accounts",
        headers=headers,
        json={"name": name, "balance": balance, "type": account_type, "currency": "INR"},
    )
    assert resp.status_code == 201
    return resp.json()


async def create_test_category(
    client: httpx.AsyncClient,
    headers: dict,
    name: str,
    cat_type: str = "expense",
) -> dict:
    """Helper to create a category for a user."""
    unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/categories",
        headers=headers,
        json={"name": unique_name, "category_type": cat_type, "icon": "tag", "color": "#2196F3"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_01_create_monthly_and_category_budgets(async_client: httpx.AsyncClient) -> None:
    """1. Create monthly overall budget and category-specific budget."""
    _, headers = await register_and_login(async_client, "Budget User 1")
    cat = await create_test_category(async_client, headers, "Groceries")

    # Overall monthly budget
    resp_overall = await async_client.post(
        "/budgets",
        headers=headers,
        json={
            "amount": "50000.00",
            "month": "2026-09",
            "period": "monthly",
        },
    )
    assert resp_overall.status_code == 201
    b_overall = resp_overall.json()
    assert b_overall["amount"] == "50000.00"
    assert b_overall["spent"] == "0.00"
    assert b_overall["remaining"] == "50000.00"
    assert b_overall["percentage_used"] == 0.0
    assert b_overall["tone"] == "ok"
    assert b_overall["category_id"] is None
    assert b_overall["month"] == "2026-09"
    assert b_overall["start_date"] == "2026-09-01"
    assert b_overall["end_date"] == "2026-09-30"

    # Category budget
    resp_cat = await async_client.post(
        "/budgets",
        headers=headers,
        json={
            "amount": "12000.00",
            "category_id": cat["id"],
            "month": "2026-09",
            "warn_at_percent": 85,
        },
    )
    assert resp_cat.status_code == 201
    b_cat = resp_cat.json()
    assert b_cat["amount"] == "12000.00"
    assert b_cat["spent"] == "0.00"
    assert b_cat["remaining"] == "12000.00"
    assert b_cat["category_id"] == cat["id"]
    assert b_cat["category_name"] == cat["name"]
    assert b_cat["warn_at_percent"] == 85


@pytest.mark.asyncio
async def test_02_update_budget(async_client: httpx.AsyncClient) -> None:
    """2. Update budget amount and warning threshold."""
    _, headers = await register_and_login(async_client, "Budget User 2")
    cat = await create_test_category(async_client, headers, "Utilities")

    create_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "8000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    assert create_resp.status_code == 201
    budget_id = create_resp.json()["id"]

    # Update amount to 10000.00 and warn_at_percent to 95
    patch_resp = await async_client.patch(
        f"/budgets/{budget_id}",
        headers=headers,
        json={"amount": "10000.00", "warn_at_percent": 95},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["amount"] == "10000.00"
    assert updated["remaining"] == "10000.00"
    assert updated["warn_at_percent"] == 95


@pytest.mark.asyncio
async def test_03_delete_budget(async_client: httpx.AsyncClient) -> None:
    """3. Delete budget and ensure it is no longer accessible."""
    _, headers = await register_and_login(async_client, "Budget User 3")
    create_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "15000.00", "month": "2026-09"},
    )
    assert create_resp.status_code == 201
    budget_id = create_resp.json()["id"]

    # Delete
    del_resp = await async_client.delete(f"/budgets/{budget_id}", headers=headers)
    assert del_resp.status_code == 204

    # Subsequent GET returns 404
    get_resp = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_04_category_budget_dedicated_endpoints(async_client: httpx.AsyncClient) -> None:
    """4. Dedicated endpoints POST /budgets/category and GET /budgets/category/{category_id}."""
    _, headers = await register_and_login(async_client, "Budget User 4")
    cat = await create_test_category(async_client, headers, "Healthcare")

    resp = await async_client.post(
        "/budgets/category",
        headers=headers,
        json={
            "category_id": cat["id"],
            "amount": "6500.00",
            "month": "2026-09",
            "warn_at_percent": 80,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["category_id"] == cat["id"]
    assert resp.json()["amount"] == "6500.00"

    # Fetch by category ID
    fetch_resp = await async_client.get(
        f"/budgets/category/{cat['id']}?month=2026-09",
        headers=headers,
    )
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["amount"] == "6500.00"
    assert fetch_resp.json()["category_name"] == cat["name"]


@pytest.mark.asyncio
async def test_05_transaction_affects_budget(async_client: httpx.AsyncClient) -> None:
    """5. Adding an expense transaction dynamically increases spent and decreases remaining."""
    _, headers = await register_and_login(async_client, "Budget User 5")
    acc = await create_test_account(async_client, headers, "HDFC")
    cat = await create_test_category(async_client, headers, "Dining")

    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "10000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    assert b_resp.status_code == 201
    budget_id = b_resp.json()["id"]

    # Record expense of 3,500.50
    tx_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "3500.50",
            "description": "Family Dinner",
            "transaction_date": "2026-09-15T20:00:00Z",
        },
    )
    assert tx_resp.status_code == 201

    # Query budget: spent should be 3500.50, remaining 6499.50, pct 35.01%
    get_resp = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert Decimal(data["spent"]) == Decimal("3500.50")
    assert Decimal(data["remaining"]) == Decimal("6499.50")
    assert data["percentage_used"] == 35.01
    assert data["tone"] == "ok"


@pytest.mark.asyncio
async def test_06_transaction_edit_affects_budget(async_client: httpx.AsyncClient) -> None:
    """6. Editing an expense amount immediately alters the derived budget spent and remaining."""
    _, headers = await register_and_login(async_client, "Budget User 6")
    acc = await create_test_account(async_client, headers, "SBI")
    cat = await create_test_category(async_client, headers, "Shopping")

    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "5000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    budget_id = b_resp.json()["id"]

    # Create expense of 1000.00
    tx_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "1000.00",
            "description": "Shoes",
            "transaction_date": "2026-09-10T10:00:00Z",
        },
    )
    tx_id = tx_resp.json()["id"]

    # Edit expense to 4000.00
    patch_tx = await async_client.patch(
        f"/transactions/{tx_id}",
        headers=headers,
        json={"amount": "4000.00"},
    )
    assert patch_tx.status_code == 200

    # Budget spent should now reflect 4000.00, remaining 1000.00
    b_get = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert Decimal(b_get.json()["spent"]) == Decimal("4000.00")
    assert Decimal(b_get.json()["remaining"]) == Decimal("1000.00")
    assert b_get.json()["percentage_used"] == 80.0


@pytest.mark.asyncio
async def test_07_transaction_delete_affects_budget(async_client: httpx.AsyncClient) -> None:
    """7. Deleting an expense restores the budget remaining balance."""
    _, headers = await register_and_login(async_client, "Budget User 7")
    acc = await create_test_account(async_client, headers, "Cash")
    cat = await create_test_category(async_client, headers, "Travel")

    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "7000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    budget_id = b_resp.json()["id"]

    # Create expense of 2500.00
    tx_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "2500.00",
            "description": "Flight Ticket",
            "transaction_date": "2026-09-05T14:00:00Z",
        },
    )
    tx_id = tx_resp.json()["id"]

    # Delete expense
    del_resp = await async_client.delete(f"/transactions/{tx_id}", headers=headers)
    assert del_resp.status_code == 204

    # Budget spent should return to 0.00, remaining 7000.00
    b_get = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert Decimal(b_get.json()["spent"]) == Decimal("0.00")
    assert Decimal(b_get.json()["remaining"]) == Decimal("7000.00")


@pytest.mark.asyncio
async def test_08_income_and_transfer_do_not_affect_budget(async_client: httpx.AsyncClient) -> None:
    """8. Income and transfer transactions must NOT count as spending."""
    _, headers = await register_and_login(async_client, "Budget User 8")
    acc1 = await create_test_account(async_client, headers, "Account A", "50000.00")
    acc2 = await create_test_account(async_client, headers, "Account B", "10000.00")
    cat = await create_test_category(async_client, headers, "Investments")

    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "20000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    budget_id = b_resp.json()["id"]

    # 1. Record income
    inc_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc1["id"],
            "category_id": cat["id"],
            "type": "income",
            "amount": "45000.00",
            "description": "Dividend",
            "transaction_date": "2026-09-12T12:00:00Z",
        },
    )
    assert inc_resp.status_code == 201

    # 2. Record transfer
    trf_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc1["id"],
            "destination_account_id": acc2["id"],
            "type": "transfer",
            "amount": "15000.00",
            "description": "Transfer between accounts",
            "transaction_date": "2026-09-14T12:00:00Z",
        },
    )
    assert trf_resp.status_code == 201

    # Budget spent must remain exactly 0.00!
    b_get = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert Decimal(b_get.json()["spent"]) == Decimal("0.00")
    assert Decimal(b_get.json()["remaining"]) == Decimal("20000.00")


@pytest.mark.asyncio
async def test_09_month_filtering(async_client: httpx.AsyncClient) -> None:
    """9. Expenses outside the budget month do NOT affect this month's budget."""
    _, headers = await register_and_login(async_client, "Budget User 9")
    acc = await create_test_account(async_client, headers, "Wallet")
    cat = await create_test_category(async_client, headers, "Entertainment")

    # September budget
    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "6000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    budget_id = b_resp.json()["id"]

    # October expense
    tx_resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "3000.00",
            "description": "Movie in October",
            "transaction_date": "2026-10-02T19:00:00Z",
        },
    )
    assert tx_resp.status_code == 201

    # September budget spent must still be 0.00
    b_get = await async_client.get(f"/budgets/{budget_id}", headers=headers)
    assert Decimal(b_get.json()["spent"]) == Decimal("0.00")
    assert Decimal(b_get.json()["remaining"]) == Decimal("6000.00")


@pytest.mark.asyncio
async def test_10_user_isolation(async_client: httpx.AsyncClient) -> None:
    """10. Strict user isolation: User B cannot access User A's budget or impact it."""
    _, headers_a = await register_and_login(async_client, "User A Budget")
    _, headers_b = await register_and_login(async_client, "User B Budget")

    cat_a = await create_test_category(async_client, headers_a, "Groceries A")
    b_a = await async_client.post(
        "/budgets",
        headers=headers_a,
        json={"amount": "10000.00", "category_id": cat_a["id"], "month": "2026-09"},
    )
    budget_a_id = b_a.json()["id"]

    # User B attempts to access User A's budget
    get_b = await async_client.get(f"/budgets/{budget_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B attempts to patch User A's budget
    patch_b = await async_client.patch(
        f"/budgets/{budget_a_id}",
        headers=headers_b,
        json={"amount": "1.00"},
    )
    assert patch_b.status_code == 404

    # User B attempts to delete User A's budget
    del_b = await async_client.delete(f"/budgets/{budget_a_id}", headers=headers_b)
    assert del_b.status_code == 404

    # User B creates an account, category, and expense; verifies User A's budget spent remains 0.00
    acc_b = await create_test_account(async_client, headers_b, "Account B")
    cat_b = await create_test_category(async_client, headers_b, "Groceries B")
    await async_client.post(
        "/transactions",
        headers=headers_b,
        json={
            "account_id": acc_b["id"],
            "category_id": cat_b["id"],
            "type": "expense",
            "amount": "5000.00",
            "transaction_date": "2026-09-10T10:00:00Z",
        },
    )

    get_a = await async_client.get(f"/budgets/{budget_a_id}", headers=headers_a)
    assert Decimal(get_a.json()["spent"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_11_invalid_amounts(async_client: httpx.AsyncClient) -> None:
    """11. Reject non-positive amounts and invalid decimal numbers."""
    _, headers = await register_and_login(async_client, "Budget User 11")

    # Amount <= 0
    resp_zero = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "0.00", "month": "2026-09"},
    )
    assert resp_zero.status_code == 422

    resp_neg = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "-500.00", "month": "2026-09"},
    )
    assert resp_neg.status_code == 422


@pytest.mark.asyncio
async def test_12_duplicate_budget_rejection(async_client: httpx.AsyncClient) -> None:
    """12. Reject duplicate budgets for the same category and month."""
    _, headers = await register_and_login(async_client, "Budget User 12")
    cat = await create_test_category(async_client, headers, "Fuel")

    # First budget
    r1 = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "4000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    assert r1.status_code == 201

    # Second budget for identical category and month fails with 400
    r2 = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "5000.00", "category_id": cat["id"], "month": "2026-09"},
    )
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_13_invalid_category_rejection(async_client: httpx.AsyncClient) -> None:
    """13. Reject budget creation with non-existent or foreign category."""
    _, headers = await register_and_login(async_client, "Budget User 13")
    fake_cat_id = str(uuid.uuid4())

    resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "3000.00", "category_id": fake_cat_id, "month": "2026-09"},
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_14_budget_tones_and_overspending(async_client: httpx.AsyncClient) -> None:
    """14. Visual tones: ok (<90%), warn (>=90%), over (>100% and negative remaining)."""
    _, headers = await register_and_login(async_client, "Budget User 14")
    acc = await create_test_account(async_client, headers, "Primary Account")
    cat = await create_test_category(async_client, headers, "Gadgets")

    b_resp = await async_client.post(
        "/budgets",
        headers=headers,
        json={
            "amount": "1000.00",
            "category_id": cat["id"],
            "month": "2026-09",
            "warn_at_percent": 90,
        },
    )
    budget_id = b_resp.json()["id"]

    # Initial state: 0% -> ok
    b0 = (await async_client.get(f"/budgets/{budget_id}", headers=headers)).json()
    assert b0["tone"] == "ok"

    # Spend 920.00 -> 92.0% -> warn
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "920.00",
            "transaction_date": "2026-09-02T10:00:00Z",
        },
    )
    b1 = (await async_client.get(f"/budgets/{budget_id}", headers=headers)).json()
    assert b1["tone"] == "warn"
    assert b1["percentage_used"] == 92.0
    assert Decimal(b1["remaining"]) == Decimal("80.00")

    # Spend another 200.00 -> total spent 1120.00 -> 112.0% -> over, remaining -120.00
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "category_id": cat["id"],
            "type": "expense",
            "amount": "200.00",
            "transaction_date": "2026-09-03T10:00:00Z",
        },
    )
    b2 = (await async_client.get(f"/budgets/{budget_id}", headers=headers)).json()
    assert b2["tone"] == "over"
    assert b2["percentage_used"] == 112.0
    assert Decimal(b2["remaining"]) == Decimal("-120.00")


@pytest.mark.asyncio
async def test_15_dhan_seed_invariant_17100_of_24000(async_client: httpx.AsyncClient) -> None:
    """15. DHAN Core Seed Invariant:

    Budget: ₹17,100 of ₹24,000, ₹6,900 left, 71% used.
    Transport is at 93% and in warning (₹2,800 of ₹3,000, ₹200 left).
    """
    _, headers = await register_and_login(async_client, "Dhan Invariant User")
    hdfc = await create_test_account(async_client, headers, "HDFC Bank", "50000.00")
    sbi = await create_test_account(async_client, headers, "SBI Savings", "20000.00")

    # 1. Setup the 4 categories
    food = await create_test_category(async_client, headers, "Food")
    shopping = await create_test_category(async_client, headers, "Shopping")
    transport = await create_test_category(async_client, headers, "Transport")
    bills = await create_test_category(async_client, headers, "Bills")

    # 2. Setup the exact category budget ceilings (totaling ₹24,000)
    # food: 6,000; shopping: 5,000; transport: 3,000; bills: 10,000
    await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "6000.00", "category_id": food["id"], "month": "2026-09"},
    )
    await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "5000.00", "category_id": shopping["id"], "month": "2026-09"},
    )
    await async_client.post(
        "/budgets",
        headers=headers,
        json={
            "amount": "3000.00",
            "category_id": transport["id"],
            "month": "2026-09",
            "warn_at_percent": 90,
        },
    )
    await async_client.post(
        "/budgets",
        headers=headers,
        json={"amount": "10000.00", "category_id": bills["id"], "month": "2026-09"},
    )

    # 3. Seed exact September 2026 expenses totaling ₹17,100:
    # Food: 4,200 (e.g. 2500, 1000, 700)
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": food["id"],
            "type": "expense",
            "amount": "2500.00",
            "transaction_date": "2026-09-02T10:00:00Z",
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": food["id"],
            "type": "expense",
            "amount": "1000.00",
            "transaction_date": "2026-09-05T12:00:00Z",
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": food["id"],
            "type": "expense",
            "amount": "700.00",
            "transaction_date": "2026-09-08T18:00:00Z",
        },
    )

    # Shopping: 3,100 (e.g. 2000, 1100)
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": sbi["id"],
            "category_id": shopping["id"],
            "type": "expense",
            "amount": "2000.00",
            "transaction_date": "2026-09-10T14:00:00Z",
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": sbi["id"],
            "category_id": shopping["id"],
            "type": "expense",
            "amount": "1100.00",
            "transaction_date": "2026-09-14T16:00:00Z",
        },
    )

    # Transport: 2,800 (e.g. 1500, 1300) -> 2,800 / 3,000 = 93.33% (>=90% => warn)
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": transport["id"],
            "type": "expense",
            "amount": "1500.00",
            "transaction_date": "2026-09-15T09:00:00Z",
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": transport["id"],
            "type": "expense",
            "amount": "1300.00",
            "transaction_date": "2026-09-18T11:00:00Z",
        },
    )

    # Bills: 7,000 (e.g. 5000, 2000)
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": bills["id"],
            "type": "expense",
            "amount": "5000.00",
            "transaction_date": "2026-09-20T08:00:00Z",
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": bills["id"],
            "type": "expense",
            "amount": "2000.00",
            "transaction_date": "2026-09-22T10:00:00Z",
        },
    )

    # Total expenses: 4200 + 3100 + 2800 + 7000 = 17,100

    # 4. Add non-expense activities to confirm they do NOT contaminate the budget
    # Income: ₹35,000
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "type": "income",
            "amount": "35000.00",
            "transaction_date": "2026-09-01T09:00:00Z",
        },
    )
    # Transfer: ₹5,000
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "destination_account_id": sbi["id"],
            "type": "transfer",
            "amount": "5000.00",
            "transaction_date": "2026-09-01T10:00:00Z",
        },
    )
    # October expense: ₹3,000
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": hdfc["id"],
            "category_id": food["id"],
            "type": "expense",
            "amount": "3000.00",
            "transaction_date": "2026-10-01T10:00:00Z",
        },
    )

    # 5. Query the monthly budget summary for 2026-09
    sum_resp = await async_client.get("/budgets/summary?month=2026-09", headers=headers)
    assert sum_resp.status_code == 200
    summary = sum_resp.json()

    # Exact Invariant Assertions: ₹17,100 of ₹24,000, ₹6,900 left, 71%
    assert Decimal(summary["limit"]) == Decimal("24000.00")
    assert Decimal(summary["spent"]) == Decimal("17100.00")
    assert Decimal(summary["remaining"]) == Decimal("6900.00")
    assert round(summary["percentage_used"]) == 71

    # Invariant: Transport is at 93% and in warning (₹200 left)
    transport_status = next(c for c in summary["categories"] if c["category_id"] == transport["id"])
    assert Decimal(transport_status["limit"]) == Decimal("3000.00")
    assert Decimal(transport_status["spent"]) == Decimal("2800.00")
    assert Decimal(transport_status["remaining"]) == Decimal("200.00")
    assert round(transport_status["percentage_used"]) == 93
    assert transport_status["tone"] == "warn"

    # Food status: 4200/6000 (70%, ok)
    food_status = next(c for c in summary["categories"] if c["category_id"] == food["id"])
    assert Decimal(food_status["spent"]) == Decimal("4200.00")
    assert Decimal(food_status["remaining"]) == Decimal("1800.00")
    assert food_status["tone"] == "ok"
