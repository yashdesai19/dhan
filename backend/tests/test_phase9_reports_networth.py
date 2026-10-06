"""Test suite for Phase 9: DHAN Reports and Net Worth.

Covers:
Seed invariants (spec §6, mock/seed.ts replayed through the API):
1. Net balance ₹1,24,580 across 5 accounts
2. September: spent ₹18,640, income ₹43,000, net flow ₹24,360, savings rate 57%
3. Category totals and counts; Bills 42.9% of spending
4. Daily spending for every day of September
5. Net worth ₹2,18,680 = assets ₹2,62,080 - liabilities ₹43,400

Date boundaries:
6. Month start and month end (half-open ranges, last microsecond, first instant)
7. Time zones: the same instant falls in different days/months per zone; DST transitions
8. Leap years (Feb 29, 2000/2100 rules) and year rollover in the trend
9. Transaction dates that are edited, deleted, or sent without an offset

Rules and safety:
10. Transfers and non-completed transactions are not income or spending
11. Savings-rate rounding matches the app (JS Math.round), Decimal precision throughout
12. Strict per-user isolation for every report, net worth, assets and liabilities
13. Validation of month, time zone, type and amounts
14. Account inclusion rules (archived, excluded, investment, card in credit)
15. Budgets and reports agree on the last day of the month
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import update

from fastapi_app.core.config import settings
from fastapi_app.core.periods import (
    assume_local,
    days_in_month,
    get_timezone,
    local_date,
    month_bounds,
    parse_month,
    shift_month,
    today_in,
)
from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.models.transaction import Transaction
from fastapi_app.services.report_service import js_round, savings_rate

IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# DHAN seed (mock/seed.ts). Balances are where each account stands on 30 Sep.
# ---------------------------------------------------------------------------

SEED_ACCOUNTS = {
    "hdfc": {"name": "HDFC Bank", "type": "bank", "balance": "86450.00"},
    "sbi": {"name": "SBI Savings", "type": "bank", "balance": "38300.00"},
    "cash": {"name": "Cash", "type": "cash", "balance": "3200.00"},
    "paytm": {"name": "Paytm Wallet", "type": "wallet", "balance": "1630.00"},
    "icici": {
        "name": "ICICI Credit Card",
        "type": "credit_card",
        "balance": "-5000.00",
        "credit_limit": "100000.00",
        "due_date": 12,
    },
    "kotak": {
        "name": "Kotak 811",
        "type": "bank",
        "balance": "0.00",
        "archived": True,
        "include_in_total": False,
    },
}

SEED_CATEGORIES = {
    "food": ("Food", "expense"),
    "transport": ("Transport", "expense"),
    "shopping": ("Shopping", "expense"),
    "bills": ("Bills", "expense"),
    "health": ("Health", "expense"),
    "fun": ("Fun and subscriptions", "expense"),
    "salary": ("Salary", "income"),
    "freelancing": ("Freelancing", "income"),
}

# (type, title, category, account, amount, local date, local time); the Goa "split" row is
# left out: the backend books group expenses through splits, and spec §6 excludes it anyway.
SEED_TRANSACTIONS = [
    ("expense", "Swiggy", "food", "hdfc", 450, "2026-09-30", "13:20"),
    ("expense", "Uber", "transport", "paytm", 280, "2026-09-30", "09:05"),
    ("expense", "Amazon", "shopping", "icici", 1299, "2026-09-29", "19:12"),
    ("transfer", "HDFC Bank → Cash", None, ("hdfc", "cash"), 5000, "2026-09-29", "11:40"),
    ("income", "Freelance", "freelancing", "sbi", 8000, "2026-09-28", "17:30"),
    ("expense", "Zomato", "food", "hdfc", 620, "2026-09-28", "21:05"),
    ("expense", "iCloud+", "bills", "hdfc", 75, "2026-09-28", "06:00"),
    ("expense", "Spotify", "bills", "hdfc", 119, "2026-09-25", "06:00"),
    ("expense", "Electricity", "bills", "hdfc", 1001, "2026-09-24", "10:15"),
    ("expense", "Swiggy", "food", "hdfc", 540, "2026-09-24", "20:40"),
    ("expense", "Apollo Pharmacy", "health", "paytm", 640, "2026-09-22", "18:10"),
    ("expense", "YouTube Premium", "bills", "hdfc", 149, "2026-09-21", "06:00"),
    ("expense", "BigBasket", "food", "sbi", 540, "2026-09-20", "11:30"),
    ("expense", "PVR Cinemas", "fun", "paytm", 300, "2026-09-19", "19:45"),
    ("expense", "Netflix", "bills", "icici", 649, "2026-09-18", "06:00"),
    ("expense", "Ola", "transport", "paytm", 560, "2026-09-17", "08:50"),
    ("expense", "Café Coffee Day", "food", "paytm", 240, "2026-09-16", "16:20"),
    ("expense", "Doctor consultation", "health", "cash", 400, "2026-09-15", "10:30"),
    ("expense", "Gas cylinder", "bills", "hdfc", 909, "2026-09-15", "09:00"),
    ("expense", "Decathlon", "shopping", "icici", 499, "2026-09-14", "17:00"),
    ("expense", "Chai Point", "food", "cash", 110, "2026-09-13", "16:00"),
    ("expense", "ChatGPT Plus", "bills", "icici", 1700, "2026-09-12", "06:00"),
    ("expense", "Petrol", "transport", "hdfc", 1000, "2026-09-12", "08:10"),
    ("expense", "Swiggy", "food", "paytm", 380, "2026-09-12", "21:30"),
    ("expense", "Steam game", "fun", "icici", 120, "2026-09-11", "22:10"),
    ("expense", "Jio recharge", "bills", "hdfc", 899, "2026-09-10", "09:30"),
    ("expense", "Domino’s", "food", "paytm", 350, "2026-09-10", "20:15"),
    ("expense", "Fruit vendor", "food", "cash", 120, "2026-09-09", "08:00"),
    ("expense", "Metro card top-up", "transport", "hdfc", 500, "2026-09-08", "08:30"),
    ("expense", "Blinkit", "food", "paytm", 310, "2026-09-08", "19:00"),
    ("expense", "Gym membership", "bills", "hdfc", 1500, "2026-09-07", "07:00"),
    ("expense", "Uber", "transport", "paytm", 340, "2026-09-06", "23:10"),
    ("expense", "Chai Point", "food", "cash", 90, "2026-09-06", "17:00"),
    ("expense", "Flipkart", "shopping", "icici", 302, "2026-09-05", "13:00"),
    ("expense", "Internet", "bills", "hdfc", 999, "2026-09-05", "06:00"),
    ("expense", "Blinkit", "food", "paytm", 260, "2026-09-04", "19:30"),
    ("expense", "Carrom club", "fun", "cash", 80, "2026-09-04", "18:00"),
    ("expense", "Rapido", "transport", "cash", 120, "2026-09-03", "09:20"),
    ("expense", "Bakery", "food", "cash", 130, "2026-09-03", "08:40"),
    ("expense", "Office canteen", "food", "cash", 60, "2026-09-02", "13:10"),
    ("income", "Salary", "salary", "hdfc", 35000, "2026-09-01", "09:00"),
]

SEED_ASSETS = [
    {"name": "Mutual funds", "asset_type": "mutual_fund", "current_value": "62000.00"},
    {"name": "EPF", "asset_type": "epf", "current_value": "48500.00"},
    {"name": "Gold", "asset_type": "gold", "current_value": "22000.00"},
]
SEED_LIABILITY = {
    "name": "Bike loan",
    "liability_type": "auto_loan",
    "total_amount": "76800.00",
    "remaining_amount": "38400.00",
    "monthly_emi": "3200.00",
}


def _opening_balances() -> dict[str, Decimal]:
    """Back-solve each account's 1 Sep balance so September's transactions land on the seed."""
    opening = {key: Decimal(acc["balance"]) for key, acc in SEED_ACCOUNTS.items()}
    for kind, _title, _cat, account, amount, _day, _time in SEED_TRANSACTIONS:
        if kind == "expense":
            opening[account] += amount
        elif kind == "income":
            opening[account] -= amount
        else:
            source, destination = account
            opening[source] += amount
            opening[destination] -= amount
    return opening


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register(client: httpx.AsyncClient, name: str) -> tuple[dict, dict]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@dhan.com"
    resp = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "SecurePassword123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["user"], {"Authorization": f"Bearer {data['access_token']}"}


async def create_account(
    client: httpx.AsyncClient, headers: dict, name: str = "Bank", **fields: object
) -> dict:
    payload = {"name": name, "type": "bank", "balance": "0.00", **fields}
    resp = await client.post("/accounts", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def post_tx(
    client: httpx.AsyncClient,
    headers: dict,
    account_id: str,
    amount: str,
    when: str,
    kind: str = "expense",
    **fields: object,
) -> dict:
    payload = {
        "account_id": account_id,
        "amount": amount,
        "type": kind,
        "transaction_date": when,
        **fields,
    }
    resp = await client.post("/transactions", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def get_json(client: httpx.AsyncClient, headers: dict, url: str) -> dict:
    resp = await client.get(url, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def seed_dhan(client: httpx.AsyncClient) -> dict:
    """Registers a user and replays the DHAN seed: accounts, categories, September, net worth."""
    _, headers = await register(client, "DHAN Seed")
    opening = _opening_balances()
    accounts = {
        key: (await create_account(client, headers, **{**acc, "balance": str(opening[key])}))["id"]
        for key, acc in SEED_ACCOUNTS.items()
    }
    categories = {}
    for key, (name, kind) in SEED_CATEGORIES.items():
        resp = await client.post(
            "/categories", headers=headers, json={"name": name, "category_type": kind}
        )
        assert resp.status_code == 201, resp.text
        categories[key] = resp.json()["id"]

    for kind, title, category, account, amount, day, time in SEED_TRANSACTIONS:
        fields: dict[str, object] = {"description": title}
        if kind == "transfer":
            source, destination = account
            fields["destination_account_id"] = accounts[destination]
            account = source
        else:
            fields["category_id"] = categories[category]
        await post_tx(
            client,
            headers,
            accounts[account],
            str(amount),
            f"{day}T{time}:00+05:30",
            kind,
            **fields,
        )

    for asset in SEED_ASSETS:
        resp = await client.post("/net-worth/assets", headers=headers, json=asset)
        assert resp.status_code == 201, resp.text
    resp = await client.post("/net-worth/liabilities", headers=headers, json=SEED_LIABILITY)
    assert resp.status_code == 201, resp.text

    return {"headers": headers, "accounts": accounts, "categories": categories}


# ==============================================================================
# SEED INVARIANTS
# ==============================================================================


@pytest.mark.asyncio
async def test_01_seed_invariants_monthly_and_net_balance(async_client: httpx.AsyncClient) -> None:
    """Net balance ₹1,24,580; September spent ₹18,640, income ₹43,000, net ₹24,360, 57%."""
    seed = await seed_dhan(async_client)
    headers = seed["headers"]

    monthly = await get_json(async_client, headers, "/reports/monthly?month=2026-09")
    assert monthly["month"] == "2026-09"
    assert monthly["timezone"] == "Asia/Kolkata"
    assert monthly["period_start"] == "2026-09-01T00:00:00+05:30"
    assert monthly["period_end"] == "2026-10-01T00:00:00+05:30"
    assert Decimal(monthly["spent"]) == Decimal("18640.00")
    assert Decimal(monthly["income"]) == Decimal("43000.00")
    assert Decimal(monthly["net"]) == Decimal("24360.00")
    assert monthly["savings_rate"] == 57
    # The ATM withdrawal is a transfer: neither income nor spending
    assert Decimal(monthly["transfers"]) == Decimal("5000.00")
    assert monthly["income_count"] == 2
    assert monthly["expense_count"] == 38

    assert [p["month"] for p in monthly["trend"]] == [
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
    ]
    assert Decimal(monthly["trend"][-1]["spent"]) == Decimal("18640.00")
    assert all(Decimal(p["spent"]) == 0 for p in monthly["trend"][:-1])

    net_worth = await get_json(async_client, headers, "/net-worth")
    assert Decimal(net_worth["net_balance"]["total"]) == Decimal("124580.00")
    assert net_worth["net_balance"]["count"] == 5
    balances = {a["name"]: Decimal(a["balance"]) for a in net_worth["accounts"]}
    assert balances == {
        "HDFC Bank": Decimal("86450.00"),
        "SBI Savings": Decimal("38300.00"),
        "Cash": Decimal("3200.00"),
        "Paytm Wallet": Decimal("1630.00"),
        "ICICI Credit Card": Decimal("-5000.00"),
    }


@pytest.mark.asyncio
async def test_02_seed_invariants_categories(async_client: httpx.AsyncClient) -> None:
    """Bills ₹8,000 (42.9%), Food ₹4,200 (14 txns), Transport ₹2,800, Shopping ₹2,100, ..."""
    seed = await seed_dhan(async_client)
    headers = seed["headers"]

    report = await get_json(async_client, headers, "/reports/categories?month=2026-09")
    assert report["type"] == "expense"
    assert Decimal(report["total"]) == Decimal("18640.00")
    assert report["count"] == 38
    rows = [(c["name"], Decimal(c["amount"]), c["count"]) for c in report["categories"]]
    assert rows == [
        ("Bills", Decimal("8000.00"), 10),
        ("Food", Decimal("4200.00"), 14),
        ("Transport", Decimal("2800.00"), 6),
        ("Shopping", Decimal("2100.00"), 3),
        ("Health", Decimal("1040.00"), 2),
        ("Fun and subscriptions", Decimal("500.00"), 3),
    ]
    shares = {c["name"]: Decimal(c["share"]) for c in report["categories"]}
    assert shares["Bills"] == Decimal("42.9")
    assert shares["Food"] == Decimal("22.5")
    assert abs(sum(shares.values()) - 100) <= Decimal("0.3")
    assert report["categories"][0]["category_id"] == seed["categories"]["bills"]

    income = await get_json(async_client, headers, "/reports/categories?month=2026-09&type=income")
    assert [(c["name"], Decimal(c["amount"])) for c in income["categories"]] == [
        ("Salary", Decimal("35000.00")),
        ("Freelancing", Decimal("8000.00")),
    ]
    assert Decimal(income["total"]) == Decimal("43000.00")


@pytest.mark.asyncio
async def test_03_seed_invariants_daily(async_client: httpx.AsyncClient) -> None:
    """Every September day is listed; the days add up to the month."""
    seed = await seed_dhan(async_client)
    daily = await get_json(async_client, seed["headers"], "/reports/daily?month=2026-09")

    assert daily["days_in_month"] == 30
    assert len(daily["days"]) == 30
    assert daily["days"][0]["date"] == "2026-09-01"
    assert daily["days"][-1]["date"] == "2026-09-30"
    by_day = {d["date"]: d for d in daily["days"]}
    assert sum(Decimal(d["spent"]) for d in daily["days"]) == Decimal("18640.00")
    assert Decimal(daily["total_spent"]) == Decimal("18640.00")
    assert Decimal(daily["total_income"]) == Decimal("43000.00")

    assert Decimal(by_day["2026-09-30"]["spent"]) == Decimal("730.00")  # Swiggy + Uber
    assert by_day["2026-09-30"]["count"] == 2
    assert Decimal(by_day["2026-09-01"]["income"]) == Decimal("35000.00")
    assert Decimal(by_day["2026-09-01"]["spent"]) == Decimal("0")
    # The ₹5,000 transfer on the 29th is not spending
    assert Decimal(by_day["2026-09-29"]["spent"]) == Decimal("1299.00")
    assert by_day["2026-09-29"]["count"] == 1

    assert daily["highest_day"]["date"] == "2026-09-12"  # ChatGPT + Petrol + Swiggy
    assert Decimal(daily["highest_day"]["spent"]) == Decimal("3080.00")
    assert daily["days_counted"] == 30
    assert Decimal(daily["average_daily_spent"]) == Decimal("621.33")


@pytest.mark.asyncio
async def test_04_seed_invariants_net_worth(async_client: httpx.AsyncClient) -> None:
    """Net worth ₹2,18,680 = assets ₹2,62,080 - liabilities ₹43,400."""
    seed = await seed_dhan(async_client)
    nw = await get_json(async_client, seed["headers"], "/net-worth")

    assert Decimal(nw["total_assets"]) == Decimal("262080.00")
    assert Decimal(nw["total_liabilities"]) == Decimal("43400.00")
    assert Decimal(nw["net_worth"]) == Decimal("218680.00")

    assets = {r["id"]: r for r in nw["assets"]}
    assert Decimal(assets["banks"]["value"]) == Decimal("124750.00")
    assert assets["banks"]["account_names"] == ["HDFC Bank", "SBI Savings"]
    assert Decimal(assets["cash"]["value"]) == Decimal("4830.00")
    assert assets["cash"]["account_names"] == ["Cash", "Paytm Wallet"]
    tracked = [(r["name"], r["type"], Decimal(r["value"])) for r in nw["assets"][2:]]
    assert tracked == [
        ("Mutual funds", "mutual_fund", Decimal("62000.00")),
        ("EPF", "epf", Decimal("48500.00")),
        ("Gold", "gold", Decimal("22000.00")),
    ]

    liabilities = [(r["name"], r["source"], Decimal(r["value"])) for r in nw["liabilities"]]
    assert liabilities == [
        ("ICICI Credit Card", "credit_card", Decimal("5000.00")),
        ("Bike loan", "liability", Decimal("38400.00")),
    ]
    assert nw["liabilities"][0]["due_day"] == 12
    # The archived Kotak account plays no part
    assert "Kotak 811" not in {a["name"] for a in nw["accounts"]}


# ==============================================================================
# DATE BOUNDARIES
# ==============================================================================


def test_05_period_helpers() -> None:
    """Month bounds are local midnights; month arithmetic crosses years; leap-year rules hold."""
    start, end = month_bounds(2026, 9, IST)
    assert start.isoformat() == "2026-09-01T00:00:00+05:30"
    assert end.isoformat() == "2026-10-01T00:00:00+05:30"
    assert (end - start) == timedelta(days=30)

    dec_start, dec_end = month_bounds(2026, 12, IST)
    assert dec_end.isoformat() == "2027-01-01T00:00:00+05:30"

    assert shift_month(2026, 1, -1) == (2025, 12)
    assert shift_month(2026, 12, 1) == (2027, 1)
    assert shift_month(2026, 9, -13) == (2025, 8)
    assert shift_month(2026, 9, 24) == (2028, 9)

    assert days_in_month(2028, 2) == 29
    assert days_in_month(2026, 2) == 28
    assert days_in_month(2000, 2) == 29  # divisible by 400
    assert days_in_month(2100, 2) == 28  # divisible by 100 but not 400

    assert parse_month("2026-09") == (2026, 9)
    for bad in ("2026-13", "2026-00", "0000-01", "9999-12", "2026/09", "2026-9-1", "abcd-ef"):
        with pytest.raises(ValueError):
            parse_month(bad)

    with pytest.raises(ValueError):
        get_timezone("Mars/Olympus_Mons")
    with pytest.raises(ValueError):
        get_timezone("../../etc/passwd")
    assert get_timezone().key == "Asia/Kolkata"

    # A naive timestamp is read as UTC: 20:00 UTC on 30 Sep is 1 Oct in India
    assert local_date(datetime(2026, 9, 30, 20, 0), IST) == date(2026, 10, 1)


@pytest.mark.asyncio
async def test_06_month_start_and_end_boundaries(async_client: httpx.AsyncClient) -> None:
    """The first instant of a month is in it; the first instant of the next month is not."""
    _, headers = await register(async_client, "Boundary User")
    acc = await create_account(async_client, headers)

    await post_tx(async_client, headers, acc["id"], "1.00", "2026-08-31T23:59:59.999999+05:30")
    await post_tx(async_client, headers, acc["id"], "10.00", "2026-09-01T00:00:00+05:30")
    await post_tx(async_client, headers, acc["id"], "100.00", "2026-09-30T23:59:59.999999+05:30")
    await post_tx(async_client, headers, acc["id"], "1000.00", "2026-10-01T00:00:00+05:30")

    async def spent(month: str) -> Decimal:
        report = await get_json(async_client, headers, f"/reports/monthly?month={month}")
        return Decimal(report["spent"])

    assert await spent("2026-08") == Decimal("1.00")
    assert await spent("2026-09") == Decimal("110.00")
    assert await spent("2026-10") == Decimal("1000.00")

    daily = await get_json(async_client, headers, "/reports/daily?month=2026-09")
    by_day = {d["date"]: Decimal(d["spent"]) for d in daily["days"]}
    assert by_day["2026-09-01"] == Decimal("10.00")
    assert by_day["2026-09-30"] == Decimal("100.00")

    categories = await get_json(async_client, headers, "/reports/categories?month=2026-09")
    assert Decimal(categories["total"]) == Decimal("110.00")


@pytest.mark.asyncio
async def test_07_time_zone_decides_the_day_and_month(async_client: httpx.AsyncClient) -> None:
    """20:00 UTC on 30 Sep is 1 Oct in India but still 30 Sep in UTC and in California."""
    _, headers = await register(async_client, "Timezone User")
    acc = await create_account(async_client, headers)
    await post_tx(async_client, headers, acc["id"], "500.00", "2026-09-30T20:00:00Z")

    async def spent(month: str, tz: str | None = None) -> Decimal:
        query = f"/reports/monthly?month={month}" + (f"&tz={tz}" if tz else "")
        return Decimal((await get_json(async_client, headers, query))["spent"])

    assert await spent("2026-09") == Decimal("0")  # default zone: India
    assert await spent("2026-10") == Decimal("500.00")
    assert await spent("2026-09", "UTC") == Decimal("500.00")
    assert await spent("2026-10", "UTC") == Decimal("0")
    assert await spent("2026-09", "America/Los_Angeles") == Decimal("500.00")

    utc_month = await get_json(async_client, headers, "/reports/monthly?month=2026-09&tz=UTC")
    assert utc_month["timezone"] == "UTC"
    assert utc_month["period_start"] == "2026-09-01T00:00:00Z"

    ist_days = await get_json(async_client, headers, "/reports/daily?month=2026-10")
    assert Decimal(ist_days["days"][0]["spent"]) == Decimal("500.00")  # 1 Oct
    utc_days = await get_json(async_client, headers, "/reports/daily?month=2026-09&tz=UTC")
    assert Decimal(utc_days["days"][-1]["spent"]) == Decimal("500.00")  # 30 Sep

    # Offsets ahead of UTC: 1 Oct 01:00 in Tokyo is 30 Sep in UTC
    await post_tx(async_client, headers, acc["id"], "7.00", "2026-10-01T01:00:00+09:00")
    assert await spent("2026-10", "Asia/Tokyo") == Decimal("507.00")
    assert await spent("2026-09", "UTC") == Decimal("507.00")


@pytest.mark.asyncio
async def test_08_daylight_saving_transitions(async_client: httpx.AsyncClient) -> None:
    """Months and days stay whole across a DST change (New York, 8 March 2026)."""
    ny = ZoneInfo("America/New_York")
    start, end = month_bounds(2026, 3, ny)
    assert start.isoformat() == "2026-03-01T00:00:00-05:00"
    assert end.isoformat() == "2026-04-01T00:00:00-04:00"
    # March is an hour short there (compare instants: same-zone subtraction is wall-clock)
    assert end.astimezone(UTC) - start.astimezone(UTC) == timedelta(days=31, hours=-1)

    _, headers = await register(async_client, "DST User")
    acc = await create_account(async_client, headers)
    await post_tx(async_client, headers, acc["id"], "1.00", "2026-03-08T06:30:00Z")  # 01:30 EST
    await post_tx(async_client, headers, acc["id"], "2.00", "2026-03-08T07:30:00Z")  # 03:30 EDT
    await post_tx(async_client, headers, acc["id"], "4.00", "2026-03-09T03:59:00Z")  # 23:59 EDT
    await post_tx(async_client, headers, acc["id"], "8.00", "2026-04-01T03:59:00Z")  # 31 Mar EDT
    await post_tx(async_client, headers, acc["id"], "16.00", "2026-04-01T04:00:00Z")  # 1 Apr

    daily = await get_json(
        async_client, headers, "/reports/daily?month=2026-03&tz=America/New_York"
    )
    by_day = {d["date"]: (Decimal(d["spent"]), d["count"]) for d in daily["days"]}
    assert by_day["2026-03-08"] == (Decimal("7.00"), 3)
    assert by_day["2026-03-31"] == (Decimal("8.00"), 1)
    assert Decimal(daily["total_spent"]) == Decimal("15.00")
    april = await get_json(
        async_client, headers, "/reports/monthly?month=2026-04&tz=America/New_York"
    )
    assert Decimal(april["spent"]) == Decimal("16.00")


@pytest.mark.asyncio
async def test_09_leap_years(async_client: httpx.AsyncClient) -> None:
    """February 2028 has 29 days and its last day counts; 2026 has 28."""
    _, headers = await register(async_client, "Leap User")
    acc = await create_account(async_client, headers)
    await post_tx(async_client, headers, acc["id"], "29.00", "2028-02-29T23:30:00+05:30")
    await post_tx(async_client, headers, acc["id"], "1.00", "2028-03-01T00:00:00+05:30")
    await post_tx(async_client, headers, acc["id"], "28.00", "2026-02-28T12:00:00+05:30")

    leap = await get_json(async_client, headers, "/reports/daily?month=2028-02")
    assert leap["days_in_month"] == 29
    assert leap["days"][-1]["date"] == "2028-02-29"
    assert Decimal(leap["days"][-1]["spent"]) == Decimal("29.00")
    assert Decimal(leap["total_spent"]) == Decimal("29.00")
    assert leap["period_end"] == "2028-03-01T00:00:00+05:30"

    common = await get_json(async_client, headers, "/reports/daily?month=2026-02")
    assert common["days_in_month"] == 28
    assert common["days"][-1]["date"] == "2026-02-28"
    assert Decimal(common["total_spent"]) == Decimal("28.00")

    march = await get_json(async_client, headers, "/reports/monthly?month=2028-03")
    assert Decimal(march["spent"]) == Decimal("1.00")


@pytest.mark.asyncio
async def test_10_year_rollover_and_trend(async_client: httpx.AsyncClient) -> None:
    """New Year's Eve and New Year's Day land in their own years; the trend crosses years."""
    _, headers = await register(async_client, "Year End User")
    acc = await create_account(async_client, headers)
    await post_tx(async_client, headers, acc["id"], "300.00", "2026-12-31T23:59:59+05:30")
    await post_tx(
        async_client, headers, acc["id"], "1000.00", "2027-01-01T00:00:00+05:30", "income"
    )
    await post_tx(async_client, headers, acc["id"], "50.00", "2027-01-01T00:00:00+05:30")

    report = await get_json(async_client, headers, "/reports/monthly?month=2027-01&months=3")
    assert [(p["month"], Decimal(p["spent"])) for p in report["trend"]] == [
        ("2026-11", Decimal("0")),
        ("2026-12", Decimal("300.00")),
        ("2027-01", Decimal("50.00")),
    ]
    assert Decimal(report["trend"][-1]["net"]) == Decimal("950.00")
    assert report["savings_rate"] == 95

    single = await get_json(async_client, headers, "/reports/monthly?month=2026-12&months=1")
    assert [p["month"] for p in single["trend"]] == ["2026-12"]

    for months in (0, 25):
        resp = await async_client.get(
            f"/reports/monthly?month=2027-01&months={months}", headers=headers
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_11_edited_and_deleted_transaction_dates(async_client: httpx.AsyncClient) -> None:
    """Moving a transaction to another month moves it in the reports; deleting removes it."""
    _, headers = await register(async_client, "Edit Date User")
    acc = await create_account(async_client, headers)
    tx = await post_tx(async_client, headers, acc["id"], "250.00", "2026-09-30T22:00:00+05:30")

    async def spent(month: str) -> Decimal:
        return Decimal(
            (await get_json(async_client, headers, f"/reports/monthly?month={month}"))["spent"]
        )

    assert (await spent("2026-09"), await spent("2026-10")) == (Decimal("250.00"), Decimal("0"))

    moved = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"transaction_date": "2026-10-01T09:00:00+05:30"},
    )
    assert moved.status_code == 200, moved.text
    assert (await spent("2026-09"), await spent("2026-10")) == (Decimal("0"), Decimal("250.00"))

    assert (
        await async_client.delete(f"/transactions/{tx['id']}", headers=headers)
    ).status_code in (
        200,
        204,
    )
    assert await spent("2026-10") == Decimal("0")


@pytest.mark.asyncio
async def test_12_timestamps_without_offset_use_dhan_time(
    async_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A transaction sent without an offset is read as DHAN local time, never the server's.

    11:30 pm on 30 Sep typed in India is September spending. Before the fix the database driver
    applied the server machine's own zone, so the month depended on where the API ran.
    """
    _, headers = await register(async_client, "Naive Date User")
    acc = await create_account(async_client, headers)
    tx = await post_tx(async_client, headers, acc["id"], "75.00", "2026-09-30T23:30:00")
    assert tx["transaction_date"] == "2026-09-30T18:00:00Z"
    sep = await get_json(async_client, headers, "/reports/monthly?month=2026-09")
    assert Decimal(sep["spent"]) == Decimal("75.00")

    edited = await async_client.patch(
        f"/transactions/{tx['id']}",
        headers=headers,
        json={"transaction_date": "2026-10-01T00:30:00"},
    )
    assert edited.json()["transaction_date"] == "2026-09-30T19:00:00Z"
    oct_ = await get_json(async_client, headers, "/reports/monthly?month=2026-10")
    assert Decimal(oct_["spent"]) == Decimal("75.00")

    # Naive list filters are read the same way: 00:15 IST on 1 Oct is after 19:00Z on 30 Sep
    later = await async_client.get("/transactions?start_date=2026-10-01T00:45:00", headers=headers)
    earlier = await async_client.get(
        "/transactions?start_date=2026-10-01T00:15:00", headers=headers
    )
    assert (len(later.json()), len(earlier.json())) == (0, 1)

    # The zone comes from configuration, not from the machine the API runs on (IST here)
    monkeypatch.setattr(settings, "DEFAULT_TIMEZONE", "UTC")
    utc_tx = await post_tx(async_client, headers, acc["id"], "5.00", "2026-09-30T23:30:00")
    assert utc_tx["transaction_date"] == "2026-09-30T23:30:00Z"
    assert assume_local(datetime(2026, 9, 30, 23, 30)).utcoffset() == timedelta(0)
    assert assume_local(datetime(2026, 9, 30, 23, 30, tzinfo=IST)).utcoffset() == timedelta(
        hours=5, minutes=30
    )


# ==============================================================================
# RULES AND PRECISION
# ==============================================================================


@pytest.mark.asyncio
async def test_13_only_completed_income_and_expenses_count(async_client: httpx.AsyncClient) -> None:
    """Transfers are reported apart; pending/failed/cancelled transactions count nowhere."""
    _, headers = await register(async_client, "Status User")
    bank = await create_account(async_client, headers, "Bank", balance="10000.00")
    wallet = await create_account(async_client, headers, "Wallet", type="wallet")
    when = "2026-09-15T12:00:00+05:30"
    await post_tx(async_client, headers, bank["id"], "1000.00", when, "income")
    await post_tx(async_client, headers, bank["id"], "200.00", when)
    await post_tx(
        async_client,
        headers,
        bank["id"],
        "3000.00",
        when,
        "transfer",
        destination_account_id=wallet["id"],
    )
    cancelled = await post_tx(async_client, headers, bank["id"], "999.00", when)
    pending_income = await post_tx(async_client, headers, bank["id"], "5000.00", when, "income")

    async with AsyncSessionLocal() as db:
        for tx_id, state in ((cancelled["id"], "cancelled"), (pending_income["id"], "pending")):
            await db.execute(
                update(Transaction).where(Transaction.id == uuid.UUID(tx_id)).values(status=state)
            )
        await db.commit()

    monthly = await get_json(async_client, headers, "/reports/monthly?month=2026-09")
    assert Decimal(monthly["income"]) == Decimal("1000.00")
    assert Decimal(monthly["spent"]) == Decimal("200.00")
    assert Decimal(monthly["transfers"]) == Decimal("3000.00")
    assert (monthly["income_count"], monthly["expense_count"]) == (1, 1)

    categories = await get_json(async_client, headers, "/reports/categories?month=2026-09")
    assert Decimal(categories["total"]) == Decimal("200.00")
    daily = await get_json(async_client, headers, "/reports/daily?month=2026-09")
    assert daily["days"][14]["count"] == 2  # 15 Sep: the income and the expense
    assert Decimal(daily["total_spent"]) == Decimal("200.00")


def test_14_savings_rate_rounding_matches_app() -> None:
    """Math.round semantics: halves go up (towards +infinity), including for negatives."""
    assert js_round(Decimal("56.651")) == 57
    assert js_round(Decimal("12.5")) == 13
    assert js_round(Decimal("12.4999")) == 12
    assert js_round(Decimal("-12.5")) == -12
    assert js_round(Decimal("-12.51")) == -13
    assert js_round(Decimal("0")) == 0

    assert savings_rate(Decimal("24360"), Decimal("43000")) == 57
    assert savings_rate(Decimal("-500"), Decimal("1000")) == -50
    assert savings_rate(Decimal("-200"), Decimal("0")) == 0  # no income: 0, like the app
    assert savings_rate(Decimal("1"), Decimal("3")) == 33


@pytest.mark.asyncio
async def test_15_overspending_and_empty_months(async_client: httpx.AsyncClient) -> None:
    """Spending more than income gives a negative net and rate; an empty month is all zeros."""
    _, headers = await register(async_client, "Overspend User")
    acc = await create_account(async_client, headers)
    await post_tx(
        async_client, headers, acc["id"], "1000.00", "2026-08-02T10:00:00+05:30", "income"
    )
    await post_tx(async_client, headers, acc["id"], "1500.00", "2026-08-03T10:00:00+05:30")
    await post_tx(async_client, headers, acc["id"], "40.00", "2026-07-03T10:00:00+05:30")

    august = await get_json(async_client, headers, "/reports/monthly?month=2026-08")
    assert Decimal(august["net"]) == Decimal("-500.00")
    assert august["savings_rate"] == -50

    july = await get_json(async_client, headers, "/reports/monthly?month=2026-07")
    assert july["savings_rate"] == 0  # spending but no income

    future = date.today().year + 2
    empty = await get_json(async_client, headers, f"/reports/monthly?month={future}-06")
    assert (Decimal(empty["income"]), Decimal(empty["spent"]), empty["savings_rate"]) == (
        Decimal("0"),
        Decimal("0"),
        0,
    )
    empty_days = await get_json(async_client, headers, f"/reports/daily?month={future}-06")
    assert empty_days["days_counted"] == 0
    assert empty_days["highest_day"] is None
    assert Decimal(empty_days["average_daily_spent"]) == Decimal("0")
    assert all(Decimal(d["spent"]) == 0 and d["count"] == 0 for d in empty_days["days"])
    empty_cats = await get_json(async_client, headers, f"/reports/categories?month={future}-06")
    assert empty_cats["categories"] == []
    assert Decimal(empty_cats["total"]) == Decimal("0")


@pytest.mark.asyncio
async def test_16_default_month_is_current_local_month(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "Default Month User")
    report = await get_json(async_client, headers, "/reports/monthly")
    assert report["month"] == today_in(IST).strftime("%Y-%m")
    daily = await get_json(async_client, headers, "/reports/daily")
    assert daily["days_counted"] == today_in(IST).day


@pytest.mark.asyncio
async def test_17_decimal_precision(async_client: httpx.AsyncClient) -> None:
    """Paise add up exactly; shares and averages are rounded once, at the end."""
    _, headers = await register(async_client, "Paise User")
    acc = await create_account(async_client, headers)
    cats = []
    for name in ("Alpha", "Beta", "Gamma"):
        resp = await async_client.post(
            "/categories", headers=headers, json={"name": name, "category_type": "expense"}
        )
        cats.append(resp.json()["id"])
    for _ in range(10):
        await post_tx(
            async_client,
            headers,
            acc["id"],
            "0.10",
            "2026-06-10T10:00:00+05:30",
            category_id=cats[0],
        )
    await post_tx(
        async_client, headers, acc["id"], "0.20", "2026-06-11T10:00:00+05:30", category_id=cats[1]
    )
    await post_tx(
        async_client, headers, acc["id"], "1.00", "2026-06-12T10:00:00+05:30", category_id=cats[2]
    )
    await post_tx(async_client, headers, acc["id"], "0.03", "2026-06-12T11:00:00+05:30")

    monthly = await get_json(async_client, headers, "/reports/monthly?month=2026-06")
    assert monthly["spent"] == "2.23"  # 10 x 0.10 + 0.20 + 1.00 + 0.03, no float drift

    cats_report = await get_json(async_client, headers, "/reports/categories?month=2026-06")
    rows = {
        c["name"]: (Decimal(c["amount"]), Decimal(c["share"])) for c in cats_report["categories"]
    }
    assert rows["Alpha"] == (Decimal("1.00"), Decimal("44.8"))
    assert rows["Gamma"] == (Decimal("1.00"), Decimal("44.8"))
    assert rows["Beta"] == (Decimal("0.20"), Decimal("9.0"))
    assert rows["Uncategorised"] == (Decimal("0.03"), Decimal("1.3"))
    assert cats_report["categories"][-1]["category_id"] is None

    daily = await get_json(async_client, headers, "/reports/daily?month=2026-06")
    assert daily["average_daily_spent"] == "0.07"  # 2.23 / 30 = 0.0743...


# ==============================================================================
# ISOLATION AND VALIDATION
# ==============================================================================


@pytest.mark.asyncio
async def test_18_reports_and_net_worth_are_per_user(async_client: httpx.AsyncClient) -> None:
    """Another user's money never shows up, in totals, rows, accounts or records."""
    seed = await seed_dhan(async_client)
    owner = seed["headers"]
    _, other = await register(async_client, "Nosy Neighbour")

    for url in (
        "/reports/monthly?month=2026-09",
        "/reports/categories?month=2026-09",
        "/reports/daily?month=2026-09",
    ):
        body = await get_json(async_client, other, url)
        for field in ("income", "spent", "transfers", "total", "total_spent", "total_income"):
            if field in body:
                assert Decimal(body[field]) == 0, (url, field)
        assert body.get("categories", []) == []
        assert body.get("highest_day") is None

    other_nw = await get_json(async_client, other, "/net-worth")
    assert other_nw["accounts"] == []
    assert Decimal(other_nw["net_worth"]) == 0
    assert other_nw["net_balance"] == {"total": "0.00", "count": 0}
    assert len(other_nw["assets"]) == 2 and all(
        Decimal(r["value"]) == 0 for r in other_nw["assets"]
    )
    assert other_nw["liabilities"] == []
    assert await get_json(async_client, other, "/net-worth/assets") == []
    assert await get_json(async_client, other, "/net-worth/liabilities") == []

    # Another user's assets and liabilities can't be read, changed or deleted
    owner_asset = (await get_json(async_client, owner, "/net-worth/assets"))[0]
    owner_loan = (await get_json(async_client, owner, "/net-worth/liabilities"))[0]
    for method, url, body in (
        ("PATCH", f"/net-worth/assets/{owner_asset['id']}", {"current_value": "1.00"}),
        ("DELETE", f"/net-worth/assets/{owner_asset['id']}", None),
        ("PATCH", f"/net-worth/liabilities/{owner_loan['id']}", {"remaining_amount": "0"}),
        ("DELETE", f"/net-worth/liabilities/{owner_loan['id']}", None),
    ):
        resp = await async_client.request(method, url, headers=other, json=body)
        assert resp.status_code == 404, (method, url)

    # The other user's own activity doesn't leak into the owner's figures either
    acc = await create_account(async_client, other, "Neighbour Bank", balance="999999.00")
    await post_tx(async_client, other, acc["id"], "777.00", "2026-09-15T12:00:00+05:30")
    owner_month = await get_json(async_client, owner, "/reports/monthly?month=2026-09")
    assert Decimal(owner_month["spent"]) == Decimal("18640.00")
    owner_nw = await get_json(async_client, owner, "/net-worth")
    assert Decimal(owner_nw["net_worth"]) == Decimal("218680.00")

    for url in ("/reports/monthly", "/reports/categories", "/reports/daily", "/net-worth"):
        assert (await async_client.get(url)).status_code == 401


@pytest.mark.asyncio
async def test_19_validation(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "Validation User")
    for url in (
        "/reports/monthly?month=2026-13",
        "/reports/monthly?month=2026-9",
        "/reports/daily?month=0000-01",
        "/reports/categories?month=abcd-ef",
        "/reports/monthly?tz=Mars/Olympus_Mons",
        "/reports/daily?tz=../../etc/passwd",
        "/reports/categories?type=transfer",
    ):
        resp = await async_client.get(url, headers=headers)
        assert resp.status_code == 422, url

    for bad in (
        {"name": "X", "asset_type": "tulips", "current_value": "1.00"},
        {"name": "X", "asset_type": "gold", "current_value": "-1.00"},
        {"name": "X", "asset_type": "gold", "current_value": "1.001"},
        {"name": "", "asset_type": "gold", "current_value": "1.00"},
    ):
        assert (
            await async_client.post("/net-worth/assets", headers=headers, json=bad)
        ).status_code == 422, bad
    for bad in (
        {
            "name": "L",
            "liability_type": "auto_loan",
            "total_amount": "10",
            "remaining_amount": "11",
        },
        {"name": "L", "liability_type": "iou", "total_amount": "10", "remaining_amount": "1"},
        {"name": "L", "liability_type": "other", "total_amount": "-1", "remaining_amount": "0"},
    ):
        assert (
            await async_client.post("/net-worth/liabilities", headers=headers, json=bad)
        ).status_code == 422, bad


# ==============================================================================
# NET WORTH RULES
# ==============================================================================


@pytest.mark.asyncio
async def test_20_assets_and_liabilities_crud(async_client: httpx.AsyncClient) -> None:
    """Revaluing, paying down and removing records moves net worth accordingly."""
    _, headers = await register(async_client, "Net Worth CRUD User")
    await create_account(async_client, headers, "Savings", balance="10000.00")
    gold = (
        await async_client.post(
            "/net-worth/assets",
            headers=headers,
            json={"name": "Gold", "asset_type": "gold", "current_value": "5000.00"},
        )
    ).json()
    loan = (
        await async_client.post(
            "/net-worth/liabilities",
            headers=headers,
            json={
                "name": "Car loan",
                "liability_type": "auto_loan",
                "total_amount": "8000.00",
                "remaining_amount": "6000.00",
                "interest_rate": "9.50",
            },
        )
    ).json()

    async def net_worth() -> Decimal:
        return Decimal((await get_json(async_client, headers, "/net-worth"))["net_worth"])

    assert await net_worth() == Decimal("9000.00")  # 10,000 + 5,000 - 6,000

    revalued = await async_client.patch(
        f"/net-worth/assets/{gold['id']}", headers=headers, json={"current_value": "5500.50"}
    )
    assert revalued.status_code == 200
    assert revalued.json()["current_value"] == "5500.50"
    assert revalued.json()["name"] == "Gold"
    paid_down = await async_client.patch(
        f"/net-worth/liabilities/{loan['id']}", headers=headers, json={"remaining_amount": "5000"}
    )
    assert paid_down.status_code == 200
    assert await net_worth() == Decimal("10500.50")

    too_much = await async_client.patch(
        f"/net-worth/liabilities/{loan['id']}", headers=headers, json={"remaining_amount": "9000"}
    )
    assert too_much.status_code == 422
    null_name = await async_client.patch(
        f"/net-worth/assets/{gold['id']}", headers=headers, json={"name": None}
    )
    assert null_name.status_code == 200 and null_name.json()["name"] == "Gold"

    assert (
        await async_client.delete(f"/net-worth/liabilities/{loan['id']}", headers=headers)
    ).status_code == 200
    assert (
        await async_client.delete(f"/net-worth/assets/{gold['id']}", headers=headers)
    ).status_code == 200
    assert await net_worth() == Decimal("10000.00")
    assert (
        await async_client.delete(f"/net-worth/assets/{gold['id']}", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_21_account_inclusion_rules(async_client: httpx.AsyncClient) -> None:
    """Excluded and archived accounts don't count; investments and card credit are assets."""
    _, headers = await register(async_client, "Inclusion User")
    await create_account(async_client, headers, "Main", balance="1000.00")
    excluded = await create_account(
        async_client, headers, "Joint", balance="500.00", include_in_total=False
    )
    assert excluded["include_in_total"] is False
    archived = await create_account(async_client, headers, "Old", balance="300.00")
    await async_client.post(f"/accounts/{archived['id']}/archive", headers=headers)
    await create_account(async_client, headers, "Demat", type="investment", balance="2000.00")
    await create_account(
        async_client, headers, "Overpaid Card", type="credit_card", balance="150.00"
    )
    await create_account(async_client, headers, "Owing Card", type="credit_card", balance="-400.00")
    await create_account(async_client, headers, "Piggy", type="other", balance="20.00")

    nw = await get_json(async_client, headers, "/net-worth")
    assert nw["net_balance"] == {"total": "2770.00", "count": 5}  # 1000+2000+150-400+20
    rows = {r["id"]: Decimal(r["value"]) for r in nw["assets"]}
    assert rows == {
        "banks": Decimal("1000.00"),
        "cash": Decimal("20.00"),
        "investments": Decimal("2000.00"),
        "card_credit": Decimal("150.00"),
    }
    assert [(r["name"], Decimal(r["value"])) for r in nw["liabilities"]] == [
        ("Overpaid Card", Decimal("0")),
        ("Owing Card", Decimal("400.00")),
    ]
    # Net worth and net balance agree when there are no tracked assets or loans
    assert Decimal(nw["net_worth"]) == Decimal("2770.00")

    listed = {a["name"]: a["included"] for a in nw["accounts"]}
    assert listed["Joint"] is False
    assert "Old" not in listed

    await async_client.patch(
        f"/accounts/{excluded['id']}", headers=headers, json={"include_in_total": True}
    )
    after = await get_json(async_client, headers, "/net-worth")
    assert after["net_balance"] == {"total": "3270.00", "count": 6}


# ==============================================================================
# CONSISTENCY WITH OTHER MODULES
# ==============================================================================


@pytest.mark.asyncio
async def test_22_budgets_and_reports_agree_on_month_end(async_client: httpx.AsyncClient) -> None:
    """Late on the last day of the month counts for that month in both budgets and reports."""
    _, headers = await register(async_client, "Budget Boundary User")
    acc = await create_account(async_client, headers, balance="10000.00")
    created = await async_client.post(
        "/budgets", headers=headers, json={"amount": "5000.00", "month": "2026-09"}
    )
    assert created.status_code == 201, created.text
    await post_tx(async_client, headers, acc["id"], "100.00", "2026-09-01T00:05:00+05:30")
    await post_tx(async_client, headers, acc["id"], "200.00", "2026-09-30T23:30:00+05:30")
    await post_tx(async_client, headers, acc["id"], "400.00", "2026-10-01T00:15:00+05:30")

    budget = await get_json(async_client, headers, "/budgets/summary?month=2026-09")
    report = await get_json(async_client, headers, "/reports/monthly?month=2026-09")
    assert Decimal(budget["spent"]) == Decimal("300.00")
    assert Decimal(report["spent"]) == Decimal("300.00")


@pytest.mark.asyncio
async def test_23_versioned_routes(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "Versioned Route User")
    for url in (
        "/api/v1/reports/monthly?month=2026-09",
        "/api/v1/reports/categories?month=2026-09",
        "/api/v1/reports/daily?month=2026-09",
        "/api/v1/net-worth",
        "/api/v1/net-worth/assets",
    ):
        assert (await async_client.get(url, headers=headers)).status_code == 200, url
