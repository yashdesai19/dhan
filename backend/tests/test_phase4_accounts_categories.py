"""Comprehensive test suite for Phase 4: DHAN Accounts and Categories.

Covers:
- Account CRUD (HDFC Savings, SBI Savings, Cash, Paytm Wallet, Credit Card)
- Category CRUD (Expense, Income, System defaults, User custom categories)
- Strict user ownership and data isolation (User A cannot access User B's accounts or categories)
- Unauthenticated authorization checks
- Archived accounts filtering, restoring, and deletion
- Credit card fields validation (credit_limit >= 0, due_date between 1 and 31)
- Duplicate name constraints per user
- Invalid payload rejection
- Pagination and query filters
- Direct database verification with SQLAlchemy AsyncSession
"""

import uuid
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.account import Account
from fastapi_app.models.category import Category


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


@pytest.mark.asyncio
async def test_01_create_and_read_all_account_types(async_client: httpx.AsyncClient) -> None:
    """Test creating HDFC Savings, SBI Savings, Cash, Paytm Wallet, and Credit Card accounts."""
    user, headers = await register_and_login(async_client, "Vikram Malhotra")

    # 1. HDFC Savings
    resp_hdfc = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "HDFC Savings",
            "type": "savings",
            "balance": "50000.50",
            "currency": "INR",
        },
    )
    assert resp_hdfc.status_code == 201
    hdfc_data = resp_hdfc.json()
    assert hdfc_data["name"] == "HDFC Savings"
    assert hdfc_data["type"] == "savings"
    assert Decimal(hdfc_data["balance"]) == Decimal("50000.50")
    assert hdfc_data["currency"] == "INR"
    assert hdfc_data["archived"] is False
    assert hdfc_data["user_id"] == user["id"]

    # 2. SBI Savings
    resp_sbi = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "SBI Savings",
            "type": "bank",
            "balance": "12000.00",
            "currency": "INR",
        },
    )
    assert resp_sbi.status_code == 201

    # 3. Cash
    resp_cash = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Cash",
            "type": "cash",
            "balance": "4500.00",
            "currency": "INR",
        },
    )
    assert resp_cash.status_code == 201

    # 4. Paytm Wallet
    resp_paytm = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Paytm Wallet",
            "type": "wallet",
            "balance": "1250.75",
            "currency": "INR",
        },
    )
    assert resp_paytm.status_code == 201

    # 5. Credit Card (with credit_limit and due_date)
    resp_cc = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Credit Card",
            "type": "credit_card",
            "balance": "0.00",
            "currency": "INR",
            "credit_limit": "150000.00",
            "due_date": 18,
        },
    )
    assert resp_cc.status_code == 201
    cc_data = resp_cc.json()
    assert cc_data["name"] == "Credit Card"
    assert cc_data["type"] == "credit_card"
    assert Decimal(cc_data["credit_limit"]) == Decimal("150000.00")
    assert cc_data["due_date"] == 18

    # List all accounts for user
    list_resp = await async_client.get("/accounts", headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 5
    names = {a["name"] for a in accounts}
    assert names == {"HDFC Savings", "SBI Savings", "Cash", "Paytm Wallet", "Credit Card"}

    # Direct database verification
    async with AsyncSessionLocal() as session:
        db_accounts = (
            (await session.execute(select(Account).where(Account.user_id == uuid.UUID(user["id"]))))
            .scalars()
            .all()
        )
        assert len(db_accounts) == 5


@pytest.mark.asyncio
async def test_02_credit_card_validations_and_invalid_data(async_client: httpx.AsyncClient) -> None:
    """Test validation constraints on credit card fields and invalid inputs."""
    _, headers = await register_and_login(async_client, "Pooja Hegde")

    # Invalid due_date > 31
    resp_invalid_due = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Invalid Due Card",
            "type": "credit_card",
            "due_date": 35,
        },
    )
    assert resp_invalid_due.status_code == 422

    # Invalid due_date < 1
    resp_invalid_due_zero = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Invalid Due Zero Card",
            "type": "credit_card",
            "due_date": 0,
        },
    )
    assert resp_invalid_due_zero.status_code == 422

    # Negative credit limit
    resp_neg_limit = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "Negative Limit Card",
            "type": "credit_card",
            "credit_limit": "-5000.00",
        },
    )
    assert resp_neg_limit.status_code == 422

    # Empty account name
    resp_empty_name = await async_client.post(
        "/accounts",
        headers=headers,
        json={
            "name": "   ",
            "type": "savings",
        },
    )
    assert resp_empty_name.status_code == 422


@pytest.mark.asyncio
async def test_03_duplicate_account_name_enforcement(async_client: httpx.AsyncClient) -> None:
    """Test that a user cannot create two active accounts with the same name, but different users can."""
    user_a, headers_a = await register_and_login(async_client, "User Alpha")
    user_b, headers_b = await register_and_login(async_client, "User Beta")

    # User A creates Emergency Fund
    resp1 = await async_client.post(
        "/accounts",
        headers=headers_a,
        json={"name": "Emergency Fund", "type": "savings", "balance": "10000.00"},
    )
    assert resp1.status_code == 201

    # User A tries to create duplicate Emergency Fund
    resp_dup = await async_client.post(
        "/accounts",
        headers=headers_a,
        json={"name": "emergency fund", "type": "savings", "balance": "5000.00"},
    )
    assert resp_dup.status_code == 400
    assert "already exists" in resp_dup.json()["detail"]

    # User B CAN create an account named Emergency Fund without collision
    resp_user_b = await async_client.post(
        "/accounts",
        headers=headers_b,
        json={"name": "Emergency Fund", "type": "savings", "balance": "20000.00"},
    )
    assert resp_user_b.status_code == 201


@pytest.mark.asyncio
async def test_04_patch_account_and_rename_conflict(async_client: httpx.AsyncClient) -> None:
    """Test updating account balance, credit card terms, and renaming."""
    _, headers = await register_and_login(async_client, "Karan Johar")

    acc1 = (
        await async_client.post(
            "/accounts",
            headers=headers,
            json={"name": "Primary Bank", "type": "savings", "balance": "1000.00"},
        )
    ).json()

    acc2 = (
        await async_client.post(
            "/accounts",
            headers=headers,
            json={"name": "Secondary Bank", "type": "savings", "balance": "500.00"},
        )
    ).json()

    # Update balance and credit terms
    patch_resp = await async_client.patch(
        f"/accounts/{acc1['id']}",
        headers=headers,
        json={"balance": "7500.25", "credit_limit": "50000.00", "due_date": 25},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert Decimal(patched["balance"]) == Decimal("7500.25")
    assert Decimal(patched["credit_limit"]) == Decimal("50000.00")
    assert patched["due_date"] == 25

    # Attempt to rename acc2 to acc1's name (Primary Bank) -> Conflict
    rename_conflict = await async_client.patch(
        f"/accounts/{acc2['id']}",
        headers=headers,
        json={"name": "primary bank"},
    )
    assert rename_conflict.status_code == 400


@pytest.mark.asyncio
async def test_05_archive_and_restore_accounts(async_client: httpx.AsyncClient) -> None:
    """Test archiving accounts, filtering archived accounts, and restoring."""
    _, headers = await register_and_login(async_client, "Sunita Rao")

    # Create active account
    acc = (
        await async_client.post(
            "/accounts",
            headers=headers,
            json={"name": "Old Savings", "type": "savings", "balance": "150.00"},
        )
    ).json()

    # Default list shows active account
    active_list = (await async_client.get("/accounts", headers=headers)).json()
    assert any(a["id"] == acc["id"] for a in active_list)

    # Archive account via DELETE /accounts/{id}
    del_resp = await async_client.delete(f"/accounts/{acc['id']}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["archived"] is True

    # Default GET /accounts should NOT show archived account
    unarchived_list = (await async_client.get("/accounts", headers=headers)).json()
    assert not any(a["id"] == acc["id"] for a in unarchived_list)

    # GET /accounts?include_archived=true DOES show archived account
    all_list = (await async_client.get("/accounts?include_archived=true", headers=headers)).json()
    assert any(a["id"] == acc["id"] for a in all_list)

    # Restore / unarchive account
    restore_resp = await async_client.patch(
        f"/accounts/{acc['id']}",
        headers=headers,
        json={"archived": False},
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["archived"] is False

    # Direct database verification
    async with AsyncSessionLocal() as session:
        db_acc = await session.get(Account, uuid.UUID(acc["id"]))
        assert db_acc is not None
        assert db_acc.archived is False
        assert db_acc.is_active is True


@pytest.mark.asyncio
async def test_06_account_strict_ownership_and_unauthorized_access(
    async_client: httpx.AsyncClient,
) -> None:
    """Security check: User A cannot read, update, or delete User B's accounts."""
    user_a, headers_a = await register_and_login(async_client, "Owner User")
    user_b, headers_b = await register_and_login(async_client, "Intruder User")

    # User A creates an account
    acc_a = (
        await async_client.post(
            "/accounts",
            headers=headers_a,
            json={"name": "Private Vault", "balance": "999999.00"},
        )
    ).json()

    # User B attempts to GET User A's account -> 404
    resp_get = await async_client.get(f"/accounts/{acc_a['id']}", headers=headers_b)
    assert resp_get.status_code == 404

    # User B attempts to PATCH User A's account -> 404
    resp_patch = await async_client.patch(
        f"/accounts/{acc_a['id']}",
        headers=headers_b,
        json={"balance": "0.00"},
    )
    assert resp_patch.status_code == 404

    # User B attempts to DELETE User A's account -> 404
    resp_del = await async_client.delete(f"/accounts/{acc_a['id']}", headers=headers_b)
    assert resp_del.status_code == 404

    # Unauthenticated request to /accounts -> 401
    resp_unauth = await async_client.get("/accounts")
    assert resp_unauth.status_code == 401

    # Verify User A's balance was not altered
    async with AsyncSessionLocal() as session:
        db_acc = await session.get(Account, uuid.UUID(acc_a["id"]))
        assert db_acc is not None
        assert Decimal(db_acc.balance) == Decimal("999999.00")


@pytest.mark.asyncio
async def test_07_get_system_categories(async_client: httpx.AsyncClient) -> None:
    """Test retrieving system default categories with type and active filters."""
    _, headers = await register_and_login(async_client, "Deepak Verma")

    resp = await async_client.get("/categories", headers=headers)
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) > 0
    # System categories have is_default == True
    assert any(c["is_default"] is True for c in categories)

    # Filter by expense
    resp_expense = await async_client.get("/categories?category_type=expense", headers=headers)
    assert resp_expense.status_code == 200
    for c in resp_expense.json():
        assert c["category_type"] == "expense"


@pytest.mark.asyncio
async def test_08_create_custom_categories_and_ordering(async_client: httpx.AsyncClient) -> None:
    """Test creating custom expense and income categories with icons, colors, and ordering."""
    user, headers = await register_and_login(async_client, "Manish Tiwari")

    # Create custom expense category
    resp_exp = await async_client.post(
        "/categories",
        headers=headers,
        json={
            "name": "Gym & Fitness",
            "category_type": "expense",
            "icon": "dumbbell",
            "color": "#FF5722",
            "ordering": 5,
        },
    )
    assert resp_exp.status_code == 201
    cat_exp = resp_exp.json()
    assert cat_exp["name"] == "Gym & Fitness"
    assert cat_exp["category_type"] == "expense"
    assert cat_exp["icon"] == "dumbbell"
    assert cat_exp["color"] == "#FF5722"
    assert cat_exp["ordering"] == 5
    assert cat_exp["is_default"] is False
    assert cat_exp["user_id"] == user["id"]

    # Create custom income category
    resp_inc = await async_client.post(
        "/categories",
        headers=headers,
        json={
            "name": "Freelance Consulting",
            "category_type": "income",
            "icon": "laptop",
            "color": "#4CAF50",
            "ordering": 1,
        },
    )
    assert resp_inc.status_code == 201
    cat_inc = resp_inc.json()
    assert cat_inc["category_type"] == "income"
    assert cat_inc["ordering"] == 1

    # Verify GET /categories includes user's custom categories
    user_cats = (await async_client.get("/categories", headers=headers)).json()
    user_cat_names = [c["name"] for c in user_cats]
    assert "Gym & Fitness" in user_cat_names
    assert "Freelance Consulting" in user_cat_names

    # Direct database verification
    async with AsyncSessionLocal() as session:
        db_cats = (
            (
                await session.execute(
                    select(Category).where(Category.user_id == uuid.UUID(user["id"]))
                )
            )
            .scalars()
            .all()
        )
        assert len(db_cats) == 2


@pytest.mark.asyncio
async def test_09_category_validations_and_duplicate_rejection(
    async_client: httpx.AsyncClient,
) -> None:
    """Test category duplicate checks and invalid category type rejection."""
    _, headers = await register_and_login(async_client, "Meera Nambiar")

    # Create category
    resp1 = await async_client.post(
        "/categories",
        headers=headers,
        json={"name": "Gaming", "category_type": "expense", "icon": "gamepad"},
    )
    assert resp1.status_code == 201

    # Attempt to create duplicate category with same name and type
    resp_dup = await async_client.post(
        "/categories",
        headers=headers,
        json={"name": "gaming", "category_type": "expense"},
    )
    assert resp_dup.status_code == 400
    assert "already exists" in resp_dup.json()["detail"]

    # Invalid category_type (not expense, income, transfer)
    resp_invalid_type = await async_client.post(
        "/categories",
        headers=headers,
        json={"name": "Crypto", "category_type": "unknown_type"},
    )
    assert resp_invalid_type.status_code == 422


@pytest.mark.asyncio
async def test_10_patch_custom_category_and_protect_system_category(
    async_client: httpx.AsyncClient,
) -> None:
    """Test updating a custom category and verifying system categories cannot be modified."""
    _, headers = await register_and_login(async_client, "Rajesh Koothrappali")

    # 1. Create custom category
    custom_cat = (
        await async_client.post(
            "/categories",
            headers=headers,
            json={"name": "Stargazing", "category_type": "expense", "icon": "telescope"},
        )
    ).json()

    # Update custom category
    patch_resp = await async_client.patch(
        f"/categories/{custom_cat['id']}",
        headers=headers,
        json={"name": "Astronomy Equipment", "ordering": 10, "is_active": False},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["name"] == "Astronomy Equipment"
    assert updated["ordering"] == 10
    assert updated["is_active"] is False

    # 2. Find a system category
    all_cats = (await async_client.get("/categories", headers=headers)).json()
    system_cat = next(c for c in all_cats if c["is_default"] is True)

    # Attempt to modify default platform category -> 403 Forbidden
    sys_patch_resp = await async_client.patch(
        f"/categories/{system_cat['id']}",
        headers=headers,
        json={"name": "Hacked System Category"},
    )
    assert sys_patch_resp.status_code == 403
    assert "Default platform categories cannot be modified" in sys_patch_resp.json()["detail"]


@pytest.mark.asyncio
async def test_11_category_strict_ownership_and_data_isolation(
    async_client: httpx.AsyncClient,
) -> None:
    """Security check: User A's custom categories are hidden and inaccessible from User B."""
    user_a, headers_a = await register_and_login(async_client, "Alice Category Owner")
    user_b, headers_b = await register_and_login(async_client, "Bob Category Intruder")

    # Alice creates private category
    cat_a = (
        await async_client.post(
            "/categories",
            headers=headers_a,
            json={"name": "Alice Private Project", "category_type": "expense"},
        )
    ).json()

    # Bob lists categories -> Must NOT contain Alice's private category
    bob_cats = (await async_client.get("/categories", headers=headers_b)).json()
    assert not any(c["id"] == cat_a["id"] for c in bob_cats)

    # Bob attempts to get Alice's category -> 404
    bob_get = await async_client.get(f"/categories/{cat_a['id']}", headers=headers_b)
    assert bob_get.status_code == 404

    # Bob attempts to patch Alice's category -> 404
    bob_patch = await async_client.patch(
        f"/categories/{cat_a['id']}",
        headers=headers_b,
        json={"name": "Bob Hijack"},
    )
    assert bob_patch.status_code == 404

    # Unauthenticated request to /categories -> 401
    unauth_resp = await async_client.get("/categories")
    assert unauth_resp.status_code == 401


@pytest.mark.asyncio
async def test_12_versioned_and_root_routing_compatibility(
    async_client: httpx.AsyncClient,
) -> None:
    """Verify endpoints operate identically via both /accounts and /api/v1/accounts."""
    _, headers = await register_and_login(async_client, "Dual Route User")

    # POST via /api/v1/accounts
    resp_v1 = await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "V1 Account", "type": "wallet", "balance": "250.00"},
    )
    assert resp_v1.status_code == 201

    # GET via root /accounts
    resp_root = await async_client.get("/accounts", headers=headers)
    assert resp_root.status_code == 200
    assert any(a["name"] == "V1 Account" for a in resp_root.json())

    # GET via /api/v1/categories
    resp_cat_v1 = await async_client.get("/api/v1/categories", headers=headers)
    assert resp_cat_v1.status_code == 200
