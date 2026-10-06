"""Comprehensive test suite for Phase 7: DHAN Splits, Groups, Split Methods, Balances, and Settlements.

Covers:
1. Split Method 1: Equal Split (including remainder paise distribution)
2. Split Method 2: Exact Amounts Split (validating exact sum equality)
3. Split Method 3: Percentage Split (validating 100% reconciliation and rounding)
4. Split Method 4: Shares (Weight-based) Split (proportional distribution)
5. Split Method 5: Item-wise Split (item-level splitting summing to total)
6. Rounding: Uneven divisions (e.g. ₹100 split 3 ways -> 33.34, 33.33, 33.33)
7. Invalid Inputs (negative amounts, percentages != 100%, exact mismatch, item mismatch)
8. Create Group and Add Members (creator is admin, add by email, duplicate prevention)
9. Group Balances Calculation (group-specific pairwise balances)
10. Partial Settlement (reducing debt balance)
11. Full Settlement (clearing debt balance to zero)
12. Duplicate Settlement Prevention (409 Conflict)
13. Settle with oneself rejection (400 Bad Request)
14. Unauthorized Group and Expense Access (isolation and 403/404)
15. Atomic Rollback Verification
16. Deleted User / Member Integrity
17. DHAN Core Seed Invariants Verification:
    - owed = ₹5,700
    - owe = ₹1,000
    - net split = ₹4,700
    - Goa trip net: +₹7,800
    - Flat 402 net: -₹3,100
    - Settling ₹1,000 with Karan leaves owed ₹5,700 and owe ₹0
"""

import uuid
from decimal import Decimal

import httpx
import pytest

from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.user import User


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
async def test_01_method_equal_split(async_client: httpx.AsyncClient) -> None:
    """1. Test Equal Split method among multiple members."""
    u1, h1 = await register_and_login(async_client, "Equal User 1")
    u2, _ = await register_and_login(async_client, "Equal User 2")
    u3, _ = await register_and_login(async_client, "Equal User 3")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])
    u3_id = uuid.UUID(u3["id"])

    # Create group
    grp_resp = await async_client.post(
        "/groups",
        headers=h1,
        json={"name": "Weekend Trip", "member_ids": [str(u2_id), str(u3_id)]},
    )
    assert grp_resp.status_code == 201
    grp_id = grp_resp.json()["id"]

    # Split ₹3,000 equally among 3 members -> 1000.00 each
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "group_id": grp_id,
            "title": "Groceries",
            "amount": "3000.00",
            "split_type": "equal",
        },
    )
    assert exp_resp.status_code == 201
    shares = exp_resp.json()["shares"]
    assert Decimal(shares[str(u1_id)]) == Decimal("1000.00")
    assert Decimal(shares[str(u2_id)]) == Decimal("1000.00")
    assert Decimal(shares[str(u3_id)]) == Decimal("1000.00")
    assert sum(Decimal(v) for v in shares.values()) == Decimal("3000.00")


@pytest.mark.asyncio
async def test_02_method_exact_amounts_split(async_client: httpx.AsyncClient) -> None:
    """2. Test Exact Split method where specific amounts are provided."""
    u1, h1 = await register_and_login(async_client, "Exact User 1")
    u2, _ = await register_and_login(async_client, "Exact User 2")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Expense of ₹2,500: User 1 owes ₹1,500.25, User 2 owes ₹999.75
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Custom Dinner",
            "amount": "2500.00",
            "split_type": "exact",
            "member_ids": [str(u1_id), str(u2_id)],
            "exact": {str(u1_id): "1500.25", str(u2_id): "999.75"},
        },
    )
    assert exp_resp.status_code == 201
    shares = exp_resp.json()["shares"]
    assert Decimal(shares[str(u1_id)]) == Decimal("1500.25")
    assert Decimal(shares[str(u2_id)]) == Decimal("999.75")
    assert sum(Decimal(v) for v in shares.values()) == Decimal("2500.00")


@pytest.mark.asyncio
async def test_03_method_percentage_split(async_client: httpx.AsyncClient) -> None:
    """3. Test Percentage Split method with exact 100% reconciliation."""
    u1, h1 = await register_and_login(async_client, "Percent User 1")
    u2, _ = await register_and_login(async_client, "Percent User 2")
    u3, _ = await register_and_login(async_client, "Percent User 3")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])
    u3_id = uuid.UUID(u3["id"])

    # Expense of ₹1,000 split 50%, 30%, 20%
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Hotel Stay",
            "amount": "1000.00",
            "split_type": "percentage",
            "member_ids": [str(u1_id), str(u2_id), str(u3_id)],
            "percentages": {str(u1_id): "50.0", str(u2_id): "30.0", str(u3_id): "20.0"},
        },
    )
    assert exp_resp.status_code == 201
    shares = exp_resp.json()["shares"]
    assert Decimal(shares[str(u1_id)]) == Decimal("500.00")
    assert Decimal(shares[str(u2_id)]) == Decimal("300.00")
    assert Decimal(shares[str(u3_id)]) == Decimal("200.00")
    assert sum(Decimal(v) for v in shares.values()) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_04_method_shares_weight_split(async_client: httpx.AsyncClient) -> None:
    """4. Test Shares (Weight-based) Split method."""
    u1, h1 = await register_and_login(async_client, "Shares User 1")
    u2, _ = await register_and_login(async_client, "Shares User 2")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Expense of ₹900 split in 2 shares and 1 share (Total 3 shares -> 600 and 300)
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Gas Refill",
            "amount": "900.00",
            "split_type": "shares",
            "member_ids": [str(u1_id), str(u2_id)],
            "shares_input": {str(u1_id): "2", str(u2_id): "1"},
        },
    )
    assert exp_resp.status_code == 201
    shares = exp_resp.json()["shares"]
    assert Decimal(shares[str(u1_id)]) == Decimal("600.00")
    assert Decimal(shares[str(u2_id)]) == Decimal("300.00")
    assert sum(Decimal(v) for v in shares.values()) == Decimal("900.00")


@pytest.mark.asyncio
async def test_05_method_itemwise_split(async_client: httpx.AsyncClient) -> None:
    """5. Test Item-wise Split method where multiple items are distributed to subsets."""
    u1, h1 = await register_and_login(async_client, "Item User 1")
    u2, _ = await register_and_login(async_client, "Item User 2")
    u3, _ = await register_and_login(async_client, "Item User 3")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])
    u3_id = uuid.UUID(u3["id"])

    # Total amount ₹1,500:
    # Item 1: Pizza ₹900 split between u1, u2, u3 (300 each)
    # Item 2: Drinks ₹600 split between u1, u2 only (300 each)
    # Expected totals: u1 = 600, u2 = 600, u3 = 300
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Italian Dinner",
            "amount": "1500.00",
            "split_type": "itemwise",
            "member_ids": [str(u1_id), str(u2_id), str(u3_id)],
            "items": [
                {
                    "title": "Pizza",
                    "amount": "900.00",
                    "member_ids": [str(u1_id), str(u2_id), str(u3_id)],
                },
                {"title": "Drinks", "amount": "600.00", "member_ids": [str(u1_id), str(u2_id)]},
            ],
        },
    )
    assert exp_resp.status_code == 201
    shares = exp_resp.json()["shares"]
    assert Decimal(shares[str(u1_id)]) == Decimal("600.00")
    assert Decimal(shares[str(u2_id)]) == Decimal("600.00")
    assert Decimal(shares[str(u3_id)]) == Decimal("300.00")
    assert sum(Decimal(v) for v in shares.values()) == Decimal("1500.00")


@pytest.mark.asyncio
async def test_06_rounding_handling_uneven_divisions(async_client: httpx.AsyncClient) -> None:
    """6. Test rounding distribution for uneven divisions without losing a single paisa."""
    u1, h1 = await register_and_login(async_client, "Round User 1")
    u2, _ = await register_and_login(async_client, "Round User 2")
    u3, _ = await register_and_login(async_client, "Round User 3")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])
    u3_id = uuid.UUID(u3["id"])

    # ₹100.00 split 3 ways -> 33.34, 33.33, 33.33 -> sum = 100.00
    r1 = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Coffee",
            "amount": "100.00",
            "split_type": "equal",
            "member_ids": [str(u1_id), str(u2_id), str(u3_id)],
        },
    )
    assert r1.status_code == 201
    s1 = r1.json()["shares"]
    shares_list = sorted([Decimal(v) for v in s1.values()], reverse=True)
    assert shares_list == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(shares_list) == Decimal("100.00")

    # Percentage split with rounding remainder (e.g. ₹10.00 split 33.33%, 33.33%, 33.34%)
    r2 = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Chai",
            "amount": "10.00",
            "split_type": "percentage",
            "member_ids": [str(u1_id), str(u2_id), str(u3_id)],
            "percentages": {str(u1_id): "33.34", str(u2_id): "33.33", str(u3_id): "33.33"},
        },
    )
    assert r2.status_code == 201
    s2 = r2.json()["shares"]
    assert sum(Decimal(v) for v in s2.values()) == Decimal("10.00")


@pytest.mark.asyncio
async def test_07_invalid_inputs_rejection(async_client: httpx.AsyncClient) -> None:
    """7. Validation tests: negative amount, percentage != 100, exact sum mismatch, item total mismatch."""
    u1, h1 = await register_and_login(async_client, "Invalid User 1")
    u2, _ = await register_and_login(async_client, "Invalid User 2")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Negative amount -> 422
    r_neg = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Bad",
            "amount": "-100.00",
            "split_type": "equal",
            "member_ids": [str(u1_id), str(u2_id)],
        },
    )
    assert r_neg.status_code == 422

    # Percentage does not sum to 100% -> 400
    r_pct = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Bad Pct",
            "amount": "1000.00",
            "split_type": "percentage",
            "member_ids": [str(u1_id), str(u2_id)],
            "percentages": {str(u1_id): "40.0", str(u2_id): "40.0"},  # Sums to 80%
        },
    )
    assert r_pct.status_code == 400
    assert "100%" in r_pct.json()["detail"]

    # Exact amounts do not sum to total -> 400
    r_exact = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Bad Exact",
            "amount": "1000.00",
            "split_type": "exact",
            "member_ids": [str(u1_id), str(u2_id)],
            "exact": {str(u1_id): "400.00", str(u2_id): "400.00"},  # Sums to 800.00
        },
    )
    assert r_exact.status_code == 400
    assert "must equal total amount" in r_exact.json()["detail"]

    # Item-wise total does not match amount -> 400
    r_item = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Bad Items",
            "amount": "1000.00",
            "split_type": "itemwise",
            "member_ids": [str(u1_id), str(u2_id)],
            "items": [{"title": "Burger", "amount": "400.00", "member_ids": [str(u1_id)]}],
        },
    )
    assert r_item.status_code == 400


@pytest.mark.asyncio
async def test_08_create_group_and_add_members(async_client: httpx.AsyncClient) -> None:
    """8. Test Group creation, automatic admin enrollment, and adding members by email/user_id."""
    u1, h1 = await register_and_login(async_client, "Group Admin")
    u2, _ = await register_and_login(async_client, "Member Alpha")
    u3, _ = await register_and_login(async_client, "Member Beta")

    # Create Group
    grp_resp = await async_client.post(
        "/groups",
        headers=h1,
        json={"name": "Flatmates", "description": "Rent and utilities", "currency": "INR"},
    )
    assert grp_resp.status_code == 201
    grp = grp_resp.json()
    grp_id = grp["id"]
    assert grp["name"] == "Flatmates"
    assert len(grp["members"]) == 1
    assert grp["members"][0]["role"] == "admin"
    assert grp["members"][0]["user_id"] == u1["id"]

    # Add member by user_id
    m2_resp = await async_client.post(
        f"/groups/{grp_id}/members",
        headers=h1,
        json={"user_id": u2["id"]},
    )
    assert m2_resp.status_code == 201
    assert m2_resp.json()["user_id"] == u2["id"]

    # Add member by email
    m3_resp = await async_client.post(
        f"/groups/{grp_id}/members",
        headers=h1,
        json={"email": u3["email"]},
    )
    assert m3_resp.status_code == 201
    assert m3_resp.json()["user_id"] == u3["id"]

    # Prevent duplicate member addition
    m3_dup = await async_client.post(
        f"/groups/{grp_id}/members",
        headers=h1,
        json={"user_id": u3["id"]},
    )
    assert m3_dup.status_code == 400


@pytest.mark.asyncio
async def test_09_group_balances_calculation(async_client: httpx.AsyncClient) -> None:
    """9. Calculate balances within a specific group."""
    u1, h1 = await register_and_login(async_client, "Balance User 1")
    u2, _ = await register_and_login(async_client, "Balance User 2")

    u2_id = uuid.UUID(u2["id"])

    grp_resp = await async_client.post(
        "/groups",
        headers=h1,
        json={"name": "Dinner Club", "member_ids": [str(u2_id)]},
    )
    grp_id = grp_resp.json()["id"]

    # User 1 pays ₹1,200 equally (600 each)
    await async_client.post(
        "/splits",
        headers=h1,
        json={
            "group_id": grp_id,
            "title": "Sushi",
            "amount": "1200.00",
            "split_type": "equal",
        },
    )

    # Query group balances for User 1: User 2 owes User 1 ₹600.00
    bal_resp = await async_client.get(f"/groups/{grp_id}/balances", headers=h1)
    assert bal_resp.status_code == 200
    pos = bal_resp.json()
    assert Decimal(pos["owed"]) == Decimal("600.00")
    assert Decimal(pos["owe"]) == Decimal("0.00")
    assert Decimal(pos["net"]) == Decimal("600.00")
    assert Decimal(pos["by_person"][str(u2_id)]) == Decimal("600.00")


@pytest.mark.asyncio
async def test_10_partial_settlement(async_client: httpx.AsyncClient) -> None:
    """10. Partial settlement: pay off a portion of debt, reducing net balance."""
    u1, h1 = await register_and_login(async_client, "Creditor")
    u2, h2 = await register_and_login(async_client, "Debtor")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Creditor pays ₹3,000 equally (Debtor owes ₹1,500)
    await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Concert",
            "amount": "3000.00",
            "split_type": "equal",
            "member_ids": [str(u1_id), str(u2_id)],
        },
    )

    # Debtor partially settles ₹500
    set_resp = await async_client.post(
        "/settlements",
        headers=h2,
        json={
            "payee_id": str(u1_id),
            "amount": "500.00",
            "method": "upi",
        },
    )
    assert set_resp.status_code == 201

    # Check creditor position: owed was 1500, now 1000
    cred_pos = (await async_client.get("/splits/balances", headers=h1)).json()
    assert Decimal(cred_pos["owed"]) == Decimal("1000.00")
    assert Decimal(cred_pos["net"]) == Decimal("1000.00")
    assert Decimal(cred_pos["by_person"][str(u2_id)]) == Decimal("1000.00")

    # Check debtor position: owe was 1500, now 1000
    debt_pos = (await async_client.get("/splits/balances", headers=h2)).json()
    assert Decimal(debt_pos["owe"]) == Decimal("1000.00")
    assert Decimal(debt_pos["net"]) == Decimal("-1000.00")
    assert Decimal(debt_pos["by_person"][str(u1_id)]) == Decimal("-1000.00")


@pytest.mark.asyncio
async def test_11_full_settlement(async_client: httpx.AsyncClient) -> None:
    """11. Full settlement: completely resolves debt to ₹0.00."""
    u1, h1 = await register_and_login(async_client, "Lender")
    u2, h2 = await register_and_login(async_client, "Borrower")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Lender pays ₹2,000 equally (Borrower owes ₹1,000)
    await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Cab",
            "amount": "2000.00",
            "split_type": "equal",
            "member_ids": [str(u1_id), str(u2_id)],
        },
    )

    # Borrower settles full ₹1,000
    await async_client.post(
        "/settlements",
        headers=h2,
        json={"payee_id": str(u1_id), "amount": "1000.00", "method": "cash"},
    )

    # Both balances should now be zero
    lender_pos = (await async_client.get("/splits/balances", headers=h1)).json()
    assert Decimal(lender_pos["owed"]) == Decimal("0.00")
    assert Decimal(lender_pos["owe"]) == Decimal("0.00")
    assert Decimal(lender_pos["net"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_12_duplicate_settlement_rejection(async_client: httpx.AsyncClient) -> None:
    """12. Reject duplicate settlement within seconds to prevent accidental double-pays."""
    u1, _ = await register_and_login(async_client, "Target Payee")
    u2, h2 = await register_and_login(async_client, "Initiating Payer")

    payload = {"payee_id": u1["id"], "amount": "750.00", "method": "upi"}

    r1 = await async_client.post("/settlements", headers=h2, json=payload)
    assert r1.status_code == 201

    # Immediate duplicate request fails with 409 Conflict
    r2 = await async_client.post("/settlements", headers=h2, json=payload)
    assert r2.status_code == 409
    assert "Duplicate settlement" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_13_settle_with_oneself_rejection(async_client: httpx.AsyncClient) -> None:
    """13. Reject attempt to settle a debt with oneself."""
    u1, h1 = await register_and_login(async_client, "Self Settler")
    r = await async_client.post(
        "/settlements",
        headers=h1,
        json={"payee_id": u1["id"], "amount": "100.00"},
    )
    assert r.status_code == 400
    assert "yourself" in r.json()["detail"]


@pytest.mark.asyncio
async def test_14_unauthorized_group_and_expense_access(async_client: httpx.AsyncClient) -> None:
    """14. Strict authorization: unauthorized users cannot view or tamper with private groups/splits."""
    _, h1 = await register_and_login(async_client, "Private Owner")
    _, h2 = await register_and_login(async_client, "Intruder")

    # User 1 creates private group
    grp_resp = await async_client.post("/groups", headers=h1, json={"name": "Secret Trip"})
    grp_id = grp_resp.json()["id"]

    # User 2 cannot access private group
    r_get = await async_client.get(f"/groups/{grp_id}", headers=h2)
    assert r_get.status_code in (403, 404)

    # User 1 creates expense
    exp_resp = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "group_id": grp_id,
            "title": "Secret Expense",
            "amount": "500.00",
            "split_type": "equal",
        },
    )
    exp_id = exp_resp.json()["id"]

    # User 2 cannot view or delete expense
    r_exp_get = await async_client.get(f"/splits/{exp_id}", headers=h2)
    assert r_exp_get.status_code in (403, 404)

    r_exp_del = await async_client.delete(f"/splits/{exp_id}", headers=h2)
    assert r_exp_del.status_code in (403, 404)


@pytest.mark.asyncio
async def test_15_atomic_rollback_on_failure(async_client: httpx.AsyncClient) -> None:
    """15. Operations must be atomic; any invalid transaction does not corrupt database state."""
    u1, h1 = await register_and_login(async_client, "Rollback User 1")
    u2, _ = await register_and_login(async_client, "Rollback User 2")

    u1_id = uuid.UUID(u1["id"])
    u2_id = uuid.UUID(u2["id"])

    # Attempt to post an expense where exact amounts don't match amount
    r = await async_client.post(
        "/splits",
        headers=h1,
        json={
            "title": "Failed Expense",
            "amount": "5000.00",
            "split_type": "exact",
            "member_ids": [str(u1_id), str(u2_id)],
            "exact": {str(u1_id): "1000.00", str(u2_id): "1000.00"},  # 2000 != 5000
        },
    )
    assert r.status_code == 400

    # Ensure balances remain untouched (0.00)
    pos = (await async_client.get("/splits/balances", headers=h1)).json()
    assert Decimal(pos["net"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_16_deleted_user_handling(async_client: httpx.AsyncClient) -> None:
    """16. Deleting a user cascades memberships without breaking overall service."""
    u1, h1 = await register_and_login(async_client, "Primary User")
    u2, _ = await register_and_login(async_client, "Temporary User")

    grp_resp = await async_client.post(
        "/groups",
        headers=h1,
        json={"name": "Temp Group", "member_ids": [u2["id"]]},
    )
    grp_id = grp_resp.json()["id"]

    # Delete u2 directly from DB session to simulate user deletion
    async with AsyncSessionLocal() as session:
        u_obj = await session.get(User, uuid.UUID(u2["id"]))
        if u_obj:
            await session.delete(u_obj)
            await session.commit()

    # Query group: should still load smoothly without 500
    g_res = await async_client.get(f"/groups/{grp_id}", headers=h1)
    assert g_res.status_code == 200


@pytest.mark.asyncio
async def test_17_dhan_seed_invariants_5700_1000_4700(async_client: httpx.AsyncClient) -> None:
    """17. Exact DHAN Core Seed Invariant:

    owed = ₹5,700
    owe = ₹1,000
    net split = ₹4,700
    Aman owes: ₹2,500
    Rahul owes: ₹3,200
    You owe Karan: ₹1,000
    Goa Trip: you get back ₹7,800 (Aman 2,400, Rahul 3,000, Karan 2,400)
    Flat 402: you owe ₹3,100
    Settling ₹1,000 with Karan leaves owed ₹5,700 and owe ₹0.
    """
    # 1. Register the 4 DHAN individuals
    me, h_me = await register_and_login(async_client, "You")
    aman, h_aman = await register_and_login(async_client, "Aman")
    rahul, h_rahul = await register_and_login(async_client, "Rahul")
    karan, h_karan = await register_and_login(async_client, "Karan")

    me_id = uuid.UUID(me["id"])
    aman_id = uuid.UUID(aman["id"])
    rahul_id = uuid.UUID(rahul["id"])
    karan_id = uuid.UUID(karan["id"])

    members = [str(me_id), str(aman_id), str(rahul_id), str(karan_id)]

    # 2. Create the 2 Groups: Goa Trip and Flat 402
    goa_resp = await async_client.post(
        "/groups",
        headers=h_me,
        json={"name": "Goa Trip", "member_ids": [str(aman_id), str(rahul_id), str(karan_id)]},
    )
    goa_id = goa_resp.json()["id"]

    flat_resp = await async_client.post(
        "/groups",
        headers=h_me,
        json={"name": "Flat 402", "member_ids": [str(aman_id), str(rahul_id), str(karan_id)]},
    )
    flat_id = flat_resp.json()["id"]

    # 3. Seed exact Goa Trip expenses:
    # (a) Beach villa: 12,000 paid by me (equal: 3000 each)
    await async_client.post(
        "/splits",
        headers=h_me,
        json={
            "group_id": goa_id,
            "title": "Beach villa · 2 nights",
            "amount": "12000.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (b) Scooter rental: 2,400 paid by aman (equal: 600 each)
    await async_client.post(
        "/splits",
        headers=h_aman,
        json={
            "group_id": goa_id,
            "title": "Scooter rental",
            "amount": "2400.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (c) Seafood dinner: 2,400 paid by karan (equal: 600 each)
    await async_client.post(
        "/splits",
        headers=h_karan,
        json={
            "group_id": goa_id,
            "title": "Seafood dinner",
            "amount": "2400.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )

    # Verify Goa Trip Net Position for me: +₹7,800 (Aman 2,400, Rahul 3,000, Karan 2,400)
    goa_pos = (await async_client.get(f"/groups/{goa_id}/balances", headers=h_me)).json()
    assert Decimal(goa_pos["net"]) == Decimal("7800.00")
    assert Decimal(goa_pos["by_person"][str(aman_id)]) == Decimal("2400.00")
    assert Decimal(goa_pos["by_person"][str(rahul_id)]) == Decimal("3000.00")
    assert Decimal(goa_pos["by_person"][str(karan_id)]) == Decimal("2400.00")

    # 4. Seed exact Flat 402 expenses:
    # (d) Rent: 12,000 paid by karan (exact: me 6000, karan 6000)
    await async_client.post(
        "/splits",
        headers=h_karan,
        json={
            "group_id": flat_id,
            "title": "Rent · September",
            "amount": "12000.00",
            "split_type": "exact",
            "member_ids": members,
            "exact": {
                str(me_id): "6000.00",
                str(aman_id): "0.00",
                str(rahul_id): "0.00",
                str(karan_id): "6000.00",
            },
        },
    )
    # (e) Groceries: 4,800 paid by me (equal: 1200 each)
    await async_client.post(
        "/splits",
        headers=h_me,
        json={
            "group_id": flat_id,
            "title": "Groceries",
            "amount": "4800.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (f) Wi-Fi: 1,200 paid by aman (equal: 300 each)
    await async_client.post(
        "/splits",
        headers=h_aman,
        json={
            "group_id": flat_id,
            "title": "Wi-Fi",
            "amount": "1200.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (g) Utilities: 4,000 paid by rahul (equal: 1000 each)
    await async_client.post(
        "/splits",
        headers=h_rahul,
        json={
            "group_id": flat_id,
            "title": "Electricity and water",
            "amount": "4000.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (h) Cleaning: 3,200 paid by aman (equal: 800 each)
    await async_client.post(
        "/splits",
        headers=h_aman,
        json={
            "group_id": flat_id,
            "title": "House cleaning",
            "amount": "3200.00",
            "split_type": "equal",
            "member_ids": members,
        },
    )
    # (i) Water purifier: 2,800 paid by me (exact: me 1400, karan 1400)
    await async_client.post(
        "/splits",
        headers=h_me,
        json={
            "group_id": flat_id,
            "title": "Water purifier service",
            "amount": "2800.00",
            "split_type": "exact",
            "member_ids": members,
            "exact": {
                str(me_id): "1400.00",
                str(aman_id): "0.00",
                str(rahul_id): "0.00",
                str(karan_id): "1400.00",
            },
        },
    )

    # Verify Flat 402 Net Position for me: -₹3,100
    flat_pos = (await async_client.get(f"/groups/{flat_id}/balances", headers=h_me)).json()
    assert Decimal(flat_pos["net"]) == Decimal("-3100.00")

    # 5. Verify OVERALL Position across all groups for 'me':
    # owed = ₹5,700, owe = ₹1,000, net split = ₹4,700
    # Aman owes +₹2,500, Rahul owes +₹3,200, Karan is owed ₹1,000 (net -₹1,000)
    overall_pos = (await async_client.get("/splits/balances", headers=h_me)).json()
    assert Decimal(overall_pos["owed"]) == Decimal("5700.00")
    assert Decimal(overall_pos["owe"]) == Decimal("1000.00")
    assert Decimal(overall_pos["net"]) == Decimal("4700.00")
    assert Decimal(overall_pos["by_person"][str(aman_id)]) == Decimal("2500.00")
    assert Decimal(overall_pos["by_person"][str(rahul_id)]) == Decimal("3200.00")
    assert Decimal(overall_pos["by_person"][str(karan_id)]) == Decimal("-1000.00")

    # 6. Settle ₹1,000 with Karan:
    # leaves owed ₹5,700 and owe ₹0 (net = ₹5,700)
    set_resp = await async_client.post(
        "/settlements",
        headers=h_me,
        json={"payee_id": str(karan_id), "amount": "1000.00", "method": "upi"},
    )
    assert set_resp.status_code == 201

    settled_pos = (await async_client.get("/splits/balances", headers=h_me)).json()
    assert Decimal(settled_pos["owed"]) == Decimal("5700.00")
    assert Decimal(settled_pos["owe"]) == Decimal("0.00")
    assert Decimal(settled_pos["net"]) == Decimal("5700.00")
