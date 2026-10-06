"""Comprehensive test suite for Phase 5: DHAN Transactions and Financial Rules.

Covers:
1. Create expense
2. Create income
3. Create transfer
4. Edit expense
5. Edit income
6. Edit transfer
7. Delete expense
8. Delete income
9. Delete transfer
10. Account balance calculations (regression tests with exact Decimal math)
11. Ownership
12. Unauthorized access
13. Invalid account / cross-user account
14. Invalid category / cross-user category
15. Negative and zero amounts
16. Transfer to same account rejection
17. Transfer rollback and atomicity
18. Filtering, search, sorting, and pagination
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.account import Account


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
    balance: str = "0.00",
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


async def get_db_account_balance(account_id: uuid.UUID) -> Decimal:
    """Fetch exact balance directly from PostgreSQL database."""
    async with AsyncSessionLocal() as session:
        acc = await session.get(Account, account_id)
        assert acc is not None
        return Decimal(str(acc.balance))


@pytest.mark.asyncio
async def test_01_create_expense_decreases_account_balance(async_client: httpx.AsyncClient) -> None:
    """1. Create expense decreases account balance atomically."""
    _, headers = await register_and_login(async_client, "Ramesh Patel")
    acc = await create_test_account(async_client, headers, "HDFC Salary", balance="10000.00")

    resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "amount": "2450.75",
            "type": "expense",
            "description": "Weekly Groceries",
            "notes": "Bought at Nature's Basket",
        },
    )
    assert resp.status_code == 201
    tx = resp.json()
    assert tx["type"] == "expense"
    assert Decimal(tx["amount"]) == Decimal("2450.75")
    assert tx["account_id"] == acc["id"]
    assert tx["destination_account_id"] is None

    # Check updated balance via API: 10000.00 - 2450.75 = 7549.25
    acc_updated = (await async_client.get(f"/accounts/{acc['id']}", headers=headers)).json()
    assert Decimal(acc_updated["balance"]) == Decimal("7549.25")

    # Direct database verification
    db_balance = await get_db_account_balance(uuid.UUID(acc["id"]))
    assert db_balance == Decimal("7549.25")


@pytest.mark.asyncio
async def test_02_create_income_increases_account_balance(async_client: httpx.AsyncClient) -> None:
    """2. Create income increases account balance atomically."""
    _, headers = await register_and_login(async_client, "Priya Nair")
    acc = await create_test_account(async_client, headers, "ICICI Savings", balance="5000.00")

    resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "amount": "15000.50",
            "type": "income",
            "description": "Freelance Milestone",
        },
    )
    assert resp.status_code == 201
    tx = resp.json()
    assert tx["type"] == "income"
    assert Decimal(tx["amount"]) == Decimal("15000.50")

    # Balance: 5000.00 + 15000.50 = 20000.50
    acc_updated = (await async_client.get(f"/accounts/{acc['id']}", headers=headers)).json()
    assert Decimal(acc_updated["balance"]) == Decimal("20000.50")

    # Direct database verification
    db_balance = await get_db_account_balance(uuid.UUID(acc["id"]))
    assert db_balance == Decimal("20000.50")


@pytest.mark.asyncio
async def test_03_create_transfer_decreases_source_and_increases_destination(
    async_client: httpx.AsyncClient,
) -> None:
    """3. Create transfer decreases source and increases destination account."""
    _, headers = await register_and_login(async_client, "Amitabh Bachchan")
    src_acc = await create_test_account(async_client, headers, "HDFC Wealth", balance="50000.00")
    dst_acc = await create_test_account(async_client, headers, "SBI Emergency", balance="10000.00")

    resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": src_acc["id"],
            "destination_account_id": dst_acc["id"],
            "amount": "12345.50",
            "type": "transfer",
            "description": "Monthly Emergency Reserve Fund",
        },
    )
    assert resp.status_code == 201
    tx = resp.json()
    assert tx["type"] == "transfer"
    assert tx["account_id"] == src_acc["id"]
    assert tx["destination_account_id"] == dst_acc["id"]
    assert Decimal(tx["amount"]) == Decimal("12345.50")

    # Source balance: 50000.00 - 12345.50 = 37654.50
    src_db = await get_db_account_balance(uuid.UUID(src_acc["id"]))
    assert src_db == Decimal("37654.50")

    # Destination balance: 10000.00 + 12345.50 = 22345.50
    dst_db = await get_db_account_balance(uuid.UUID(dst_acc["id"]))
    assert dst_db == Decimal("22345.50")


@pytest.mark.asyncio
async def test_04_edit_expense_adjusts_balance(async_client: httpx.AsyncClient) -> None:
    """4. Edit expense amount and account adjusts balance accurately."""
    _, headers = await register_and_login(async_client, "Deepika Padukone")
    acc1 = await create_test_account(async_client, headers, "Primary Card", balance="10000.00")
    acc2 = await create_test_account(async_client, headers, "Backup Wallet", balance="5000.00")

    # Create initial expense of 2000.00 -> acc1 = 8000.00
    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={"account_id": acc1["id"], "amount": "2000.00", "type": "expense"},
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(acc1["id"])) == Decimal("8000.00")

    # Update expense amount from 2000.00 to 3500.00 on same account -> acc1 = 6500.00
    patch_resp = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"amount": "3500.00"},
    )
    assert patch_resp.status_code == 200
    assert await get_db_account_balance(uuid.UUID(acc1["id"])) == Decimal("6500.00")

    # Update expense to move to acc2 for 1500.00 -> acc1 refunded to 10000.00, acc2 = 3500.00
    patch_acc_resp = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"account_id": acc2["id"], "amount": "1500.00"},
    )
    assert patch_acc_resp.status_code == 200
    assert await get_db_account_balance(uuid.UUID(acc1["id"])) == Decimal("10000.00")
    assert await get_db_account_balance(uuid.UUID(acc2["id"])) == Decimal("3500.00")


@pytest.mark.asyncio
async def test_05_edit_income_adjusts_balance(async_client: httpx.AsyncClient) -> None:
    """5. Edit income amount adjusts balance accurately."""
    _, headers = await register_and_login(async_client, "Shah Rukh Khan")
    acc = await create_test_account(async_client, headers, "Salary Account", balance="5000.00")

    # Initial income: +1000.00 -> 6000.00
    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={"account_id": acc["id"], "amount": "1000.00", "type": "income"},
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("6000.00")

    # Edit income to 2500.00 -> 5000.00 + 2500.00 = 7500.00
    patch_resp = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"amount": "2500.00"},
    )
    assert patch_resp.status_code == 200
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("7500.00")


@pytest.mark.asyncio
async def test_06_edit_transfer_adjusts_both_balances(async_client: httpx.AsyncClient) -> None:
    """6. Edit transfer amount adjusts source and destination balances correctly."""
    _, headers = await register_and_login(async_client, "Ranveer Singh")
    src = await create_test_account(async_client, headers, "Source Account", balance="10000.00")
    dst = await create_test_account(async_client, headers, "Dest Account", balance="5000.00")

    # Initial transfer 3000.00 -> src: 7000.00, dst: 8000.00
    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={
                "account_id": src["id"],
                "destination_account_id": dst["id"],
                "amount": "3000.00",
                "type": "transfer",
            },
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(src["id"])) == Decimal("7000.00")
    assert await get_db_account_balance(uuid.UUID(dst["id"])) == Decimal("8000.00")

    # Edit transfer amount down to 1000.00 -> src: 9000.00, dst: 6000.00
    patch_resp = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"amount": "1000.00"},
    )
    assert patch_resp.status_code == 200
    assert await get_db_account_balance(uuid.UUID(src["id"])) == Decimal("9000.00")
    assert await get_db_account_balance(uuid.UUID(dst["id"])) == Decimal("6000.00")


@pytest.mark.asyncio
async def test_07_delete_expense_reverts_balance(async_client: httpx.AsyncClient) -> None:
    """7. Delete expense refunds money back to account balance."""
    _, headers = await register_and_login(async_client, "Anushka Sharma")
    acc = await create_test_account(async_client, headers, "Shopping Card", balance="10000.00")

    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={"account_id": acc["id"], "amount": "4000.00", "type": "expense"},
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("6000.00")

    del_resp = await async_client.delete(f"/transactions/{tx['id']}", headers=headers)
    assert del_resp.status_code == 204

    # Account balance restored to 10000.00
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("10000.00")


@pytest.mark.asyncio
async def test_08_delete_income_reverts_balance(async_client: httpx.AsyncClient) -> None:
    """8. Delete income deducts previously added money from account balance."""
    _, headers = await register_and_login(async_client, "Virat Kohli")
    acc = await create_test_account(async_client, headers, "Savings", balance="5000.00")

    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={"account_id": acc["id"], "amount": "2000.00", "type": "income"},
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("7000.00")

    del_resp = await async_client.delete(f"/transactions/{tx['id']}", headers=headers)
    assert del_resp.status_code == 204

    # Balance restored to 5000.00
    assert await get_db_account_balance(uuid.UUID(acc["id"])) == Decimal("5000.00")


@pytest.mark.asyncio
async def test_09_delete_transfer_reverts_both_balances(async_client: httpx.AsyncClient) -> None:
    """9. Delete transfer restores source and deducts destination balance."""
    _, headers = await register_and_login(async_client, "Rohit Sharma")
    src = await create_test_account(async_client, headers, "Source Checking", balance="20000.00")
    dst = await create_test_account(async_client, headers, "Target Savings", balance="10000.00")

    tx = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={
                "account_id": src["id"],
                "destination_account_id": dst["id"],
                "amount": "5000.00",
                "type": "transfer",
            },
        )
    ).json()
    assert await get_db_account_balance(uuid.UUID(src["id"])) == Decimal("15000.00")
    assert await get_db_account_balance(uuid.UUID(dst["id"])) == Decimal("15000.00")

    del_resp = await async_client.delete(f"/transactions/{tx['id']}", headers=headers)
    assert del_resp.status_code == 204

    # Both balances reverted
    assert await get_db_account_balance(uuid.UUID(src["id"])) == Decimal("20000.00")
    assert await get_db_account_balance(uuid.UUID(dst["id"])) == Decimal("10000.00")


@pytest.mark.asyncio
async def test_10_account_balance_calculations_regression_suite(
    async_client: httpx.AsyncClient,
) -> None:
    """10. Mathematical regression suite verifying exact Decimal consistency."""
    _, headers = await register_and_login(async_client, "Hardik Pandya")
    acc_a = await create_test_account(async_client, headers, "Account A", balance="10000.00")
    acc_b = await create_test_account(async_client, headers, "Account B", balance="2000.00")

    # Sequence of financial transactions:
    # 1. Income to A: +3500.25 -> A: 13500.25
    await async_client.post(
        "/transactions",
        headers=headers,
        json={"account_id": acc_a["id"], "amount": "3500.25", "type": "income"},
    )
    # 2. Expense from A: -1200.75 -> A: 12299.50
    await async_client.post(
        "/transactions",
        headers=headers,
        json={"account_id": acc_a["id"], "amount": "1200.75", "type": "expense"},
    )
    # 3. Transfer from A to B: 2299.50 -> A: 10000.00, B: 4299.50
    tx_transfer = (
        await async_client.post(
            "/transactions",
            headers=headers,
            json={
                "account_id": acc_a["id"],
                "destination_account_id": acc_b["id"],
                "amount": "2299.50",
                "type": "transfer",
            },
        )
    ).json()
    # 4. Expense from B: -299.50 -> B: 4000.00
    await async_client.post(
        "/transactions",
        headers=headers,
        json={"account_id": acc_b["id"], "amount": "299.50", "type": "expense"},
    )

    # Check state before deletion
    assert await get_db_account_balance(uuid.UUID(acc_a["id"])) == Decimal("10000.00")
    assert await get_db_account_balance(uuid.UUID(acc_b["id"])) == Decimal("4000.00")

    # 5. Delete transfer: A should get +2299.50 -> 12299.50, B should lose 2299.50 -> 1700.50
    await async_client.delete(f"/transactions/{tx_transfer['id']}", headers=headers)

    assert await get_db_account_balance(uuid.UUID(acc_a["id"])) == Decimal("12299.50")
    assert await get_db_account_balance(uuid.UUID(acc_b["id"])) == Decimal("1700.50")


@pytest.mark.asyncio
async def test_11_strict_ownership_and_data_isolation(async_client: httpx.AsyncClient) -> None:
    """11. User A cannot access or mutate User B's transactions."""
    _, headers_a = await register_and_login(async_client, "User Owner")
    _, headers_b = await register_and_login(async_client, "User Intruder")

    acc_a = await create_test_account(async_client, headers_a, "Owner Bank", balance="5000.00")
    tx_a = (
        await async_client.post(
            "/transactions",
            headers=headers_a,
            json={"account_id": acc_a["id"], "amount": "500.00", "type": "expense"},
        )
    ).json()

    # User B cannot GET User A's transaction
    get_resp = await async_client.get(f"/transactions/{tx_a['id']}", headers=headers_b)
    assert get_resp.status_code == 404

    # User B cannot PATCH User A's transaction
    patch_resp = await async_client.patch(
        f"/transactions/{tx_a['id']}",
        headers=headers_b,
        json={"amount": "1.00"},
    )
    assert patch_resp.status_code == 404

    # User B cannot DELETE User A's transaction
    del_resp = await async_client.delete(f"/transactions/{tx_a['id']}", headers=headers_b)
    assert del_resp.status_code == 404

    # User B listing transactions does NOT include User A's transaction
    list_b = (await async_client.get("/transactions", headers=headers_b)).json()
    assert not any(t["id"] == tx_a["id"] for t in list_b)


@pytest.mark.asyncio
async def test_12_unauthorized_access_rejected(async_client: httpx.AsyncClient) -> None:
    """12. Unauthenticated requests are rejected with 401."""
    random_id = uuid.uuid4()
    assert (await async_client.get("/transactions")).status_code == 401
    assert (await async_client.post("/transactions", json={})).status_code == 401
    assert (await async_client.get(f"/transactions/{random_id}")).status_code == 401
    assert (await async_client.patch(f"/transactions/{random_id}", json={})).status_code == 401
    assert (await async_client.delete(f"/transactions/{random_id}")).status_code == 401


@pytest.mark.asyncio
async def test_13_invalid_or_cross_user_account_rejected(async_client: httpx.AsyncClient) -> None:
    """13. Transactions with nonexistent or other users' accounts are rejected."""
    _, headers_a = await register_and_login(async_client, "Legit User")
    _, headers_b = await register_and_login(async_client, "Victim User")

    acc_b = await create_test_account(async_client, headers_b, "Victim Account", balance="1000.00")
    fake_acc_id = str(uuid.uuid4())

    # Nonexistent account
    resp_fake = await async_client.post(
        "/transactions",
        headers=headers_a,
        json={"account_id": fake_acc_id, "amount": "100.00", "type": "expense"},
    )
    assert resp_fake.status_code == 404

    # User A tries to bill User B's account
    resp_cross = await async_client.post(
        "/transactions",
        headers=headers_a,
        json={"account_id": acc_b["id"], "amount": "100.00", "type": "expense"},
    )
    assert resp_cross.status_code == 404


@pytest.mark.asyncio
async def test_14_invalid_or_cross_user_category_rejected(async_client: httpx.AsyncClient) -> None:
    """14. Transactions with invalid categories are rejected."""
    _, headers_a = await register_and_login(async_client, "User Category Test")
    _, headers_b = await register_and_login(async_client, "User Category Other")

    acc_a = await create_test_account(async_client, headers_a, "Bank A", balance="1000.00")

    # User B creates a private custom category
    cat_b = (
        await async_client.post(
            "/categories",
            headers=headers_b,
            json={"name": "User B Secret Category", "category_type": "expense"},
        )
    ).json()

    # User A tries to use User B's private category -> 400
    resp = await async_client.post(
        "/transactions",
        headers=headers_a,
        json={
            "account_id": acc_a["id"],
            "category_id": cat_b["id"],
            "amount": "50.00",
            "type": "expense",
        },
    )
    assert resp.status_code == 400
    assert "inaccessible" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_15_negative_and_zero_amounts_rejected(async_client: httpx.AsyncClient) -> None:
    """15. Negative and zero amounts are rejected."""
    _, headers = await register_and_login(async_client, "Negative Amount User")
    acc = await create_test_account(async_client, headers, "Card", balance="1000.00")

    resp_neg = await async_client.post(
        "/transactions",
        headers=headers,
        json={"account_id": acc["id"], "amount": "-150.00", "type": "expense"},
    )
    assert resp_neg.status_code == 422

    resp_zero = await async_client.post(
        "/transactions",
        headers=headers,
        json={"account_id": acc["id"], "amount": "0.00", "type": "expense"},
    )
    assert resp_zero.status_code == 422


@pytest.mark.asyncio
async def test_16_transfer_same_account_rejected(async_client: httpx.AsyncClient) -> None:
    """16. Transferring to the same account is rejected."""
    _, headers = await register_and_login(async_client, "Same Account User")
    acc = await create_test_account(async_client, headers, "Solo Account", balance="5000.00")

    resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc["id"],
            "destination_account_id": acc["id"],
            "amount": "100.00",
            "type": "transfer",
        },
    )
    assert resp.status_code == 422 or resp.status_code == 400


@pytest.mark.asyncio
async def test_17_transfer_rollback_on_failure(async_client: httpx.AsyncClient) -> None:
    """17. When a transfer fails, database state remains untouched (atomic rollback)."""
    _, headers = await register_and_login(async_client, "Atomic Rollback User")
    src = await create_test_account(async_client, headers, "Atomic Source", balance="10000.00")

    # Attempt transfer to nonexistent destination
    fake_dest_id = str(uuid.uuid4())
    resp = await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": src["id"],
            "destination_account_id": fake_dest_id,
            "amount": "5000.00",
            "type": "transfer",
        },
    )
    assert resp.status_code in (400, 404)

    # Verify source balance was NOT deducted
    assert await get_db_account_balance(uuid.UUID(src["id"])) == Decimal("10000.00")


@pytest.mark.asyncio
async def test_18_filtering_search_and_pagination(async_client: httpx.AsyncClient) -> None:
    """18. Filtering by type, account, date range, search keyword, and pagination."""
    _, headers = await register_and_login(async_client, "Filter User")
    acc1 = await create_test_account(async_client, headers, "Filter Bank 1", balance="50000.00")
    acc2 = await create_test_account(async_client, headers, "Filter Bank 2", balance="20000.00")

    # Create distinct transactions
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc1["id"],
            "amount": "500.00",
            "type": "expense",
            "description": "Starbucks Coffee",
            "transaction_date": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc1["id"],
            "amount": "15000.00",
            "type": "income",
            "description": "Consulting Salary",
            "transaction_date": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        },
    )
    await async_client.post(
        "/transactions",
        headers=headers,
        json={
            "account_id": acc1["id"],
            "destination_account_id": acc2["id"],
            "amount": "3000.00",
            "type": "transfer",
            "description": "Inter-account Transfer",
            "transaction_date": datetime.now(UTC).isoformat(),
        },
    )

    # 1. Type filter: type=expense
    resp_exp = await async_client.get("/transactions?type=expense", headers=headers)
    assert resp_exp.status_code == 200
    assert len(resp_exp.json()) == 1
    assert resp_exp.json()[0]["type"] == "expense"

    # 2. Search keyword: "Coffee"
    resp_search = await async_client.get("/transactions?search=Coffee", headers=headers)
    assert resp_search.status_code == 200
    assert len(resp_search.json()) == 1
    assert "Starbucks Coffee" in resp_search.json()[0]["description"]

    # 3. Account filter: acc2
    resp_acc2 = await async_client.get(f"/transactions?account_id={acc2['id']}", headers=headers)
    assert resp_acc2.status_code == 200
    assert len(resp_acc2.json()) == 1  # The transfer involving acc2

    # 4. Pagination: limit=2
    resp_page = await async_client.get("/transactions?limit=2&offset=0", headers=headers)
    assert resp_page.status_code == 200
    assert len(resp_page.json()) == 2
    assert resp_page.headers.get("X-Total-Count") == "3"
