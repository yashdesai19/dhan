"""Test suite for Phase 10: DHAN AI backend.

Covers:
1. Conversation creation (default and explicit titles, validation)
2. Message creation: a question and its answer saved as consecutive turns
3. History: ordering, limits, message counts, titles, concurrency-safe numbering
4. Mock responses for every supported topic, computed from the user's own data
5. User isolation: conversations, messages, and the data a provider is shown
6. Unauthorized access: no token, bad token, someone else's conversation
7. Provider abstraction: replaceable via dependency, failure and misconfiguration (503,
   nothing saved), history handed to the provider
8. Intent classification and month resolution
"""

import asyncio
import json
import uuid
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from fastapi_app.ai.intents import Intent, classify, resolve_month
from fastapi_app.ai.providers import (
    AIProvider,
    MockProvider,
    ProviderReply,
    ProviderRequest,
    Stat,
    get_ai_provider,
)
from fastapi_app.ai.service import title_from
from fastapi_app.core.config import settings
from fastapi_app.core.periods import get_timezone, today_in
from fastapi_app.db.session import AsyncSessionLocal
from fastapi_app.main import app
from fastapi_app.models.ai import AIConversation, AIMessage

TODAY = today_in(get_timezone())
THIS_MONTH = f"{TODAY:%B %Y}"


def at_ist(day: date, hhmm: str = "00:05") -> str:
    return f"{day.isoformat()}T{hhmm}:00+05:30"


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


async def new_conversation(client: httpx.AsyncClient, headers: dict, **body: str) -> dict:
    resp = await client.post("/ai/conversations", headers=headers, json=body or None)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def ask(
    client: httpx.AsyncClient, headers: dict, conversation_id: str, question: str
) -> dict:
    resp = await client.post(
        f"/ai/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": question},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def answer(client: httpx.AsyncClient, headers: dict, question: str) -> dict:
    """Asks in a fresh conversation and returns the assistant's message."""
    conversation = await new_conversation(client, headers)
    return (await ask(client, headers, conversation["id"], question))["assistant_message"]


async def create(client: httpx.AsyncClient, headers: dict, url: str, body: dict) -> dict:
    resp = await client.post(url, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def seed_finances(client: httpx.AsyncClient, headers: dict, scale: int = 1) -> dict:
    """A small, exact data set in the current month. scale distinguishes users' figures."""
    bank = await create(
        client,
        headers,
        "/accounts",
        {"name": f"Bank x{scale}", "type": "bank", "balance": str(50000 * scale)},
    )
    food = await create(
        client, headers, "/categories", {"name": f"Food{scale}", "category_type": "expense"}
    )
    for amount, title in ((1000, "Swiggy"), (500, "Zomato")):
        await create(
            client,
            headers,
            "/transactions",
            {
                "account_id": bank["id"],
                "amount": str(amount * scale),
                "type": "expense",
                "category_id": food["id"],
                "description": f"{title}{scale}",
                "transaction_date": at_ist(TODAY),
            },
        )
    await create(
        client,
        headers,
        "/transactions",
        {
            "account_id": bank["id"],
            "amount": str(10000 * scale),
            "type": "income",
            "description": "Salary",
            "transaction_date": at_ist(TODAY),
        },
    )
    return {"bank": bank, "food": food}


class RecordingProvider(AIProvider):
    """Stands in for a hosted model and keeps every request it's shown."""

    name = "recording"

    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    async def generate(self, request: ProviderRequest) -> ProviderReply:
        self.requests.append(request)
        return ProviderReply(content=f"Recorded #{len(self.requests)}", stats=[Stat("n", "1")])


class FailingProvider(AIProvider):
    name = "failing"

    async def generate(self, request: ProviderRequest) -> ProviderReply:
        raise RuntimeError("upstream model timed out")


@pytest.fixture
def use_provider():
    """Swap the provider for the duration of a test, as a real one would be swapped in."""

    def install(provider: AIProvider) -> AIProvider:
        app.dependency_overrides[get_ai_provider] = lambda: provider
        return provider

    yield install
    app.dependency_overrides.pop(get_ai_provider, None)


# ==============================================================================
# CONVERSATIONS, MESSAGES AND HISTORY
# ==============================================================================


@pytest.mark.asyncio
async def test_01_conversation_creation(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Create User")

    untitled = await new_conversation(async_client, headers)
    assert untitled["title"] == ""
    assert untitled["message_count"] == 0
    titled = await new_conversation(async_client, headers, title="  Budget check-in  ")
    assert titled["title"] == "Budget check-in"

    listed = (await async_client.get("/ai/conversations", headers=headers)).json()
    assert {c["id"] for c in listed} == {untitled["id"], titled["id"]}

    too_long = await async_client.post(
        "/ai/conversations", headers=headers, json={"title": "x" * 121}
    )
    assert too_long.status_code == 422


@pytest.mark.asyncio
async def test_02_message_creation(async_client: httpx.AsyncClient) -> None:
    """A question and its answer are saved together as turns 1 and 2."""
    _, headers = await register(async_client, "AI Message User")
    conversation = await new_conversation(async_client, headers)

    exchange = await ask(
        async_client, headers, conversation["id"], "  How much did I spend this month?  "
    )
    question, reply = exchange["user_message"], exchange["assistant_message"]
    assert (question["seq"], question["role"]) == (1, "user")
    assert question["content"] == "How much did I spend this month?"
    assert question["intent"] is None and question["stats"] == [] and question["provider"] is None
    assert (reply["seq"], reply["role"]) == (2, "assistant")
    assert reply["intent"] == "spending_summary"
    assert reply["provider"] == "mock"
    assert reply["content"]
    assert reply["conversation_id"] == question["conversation_id"] == conversation["id"]
    assert exchange["conversation"]["message_count"] == 2
    # The first question names an untitled conversation
    assert exchange["conversation"]["title"] == "How much did I spend this month?"


@pytest.mark.asyncio
async def test_03_history(async_client: httpx.AsyncClient) -> None:
    """History comes back oldest first; limits keep the latest turns; lists sort by activity."""
    _, headers = await register(async_client, "AI History User")
    first = await new_conversation(async_client, headers)
    second = await new_conversation(async_client, headers)

    questions = ["What's my net worth?", "Show my recent expenses", "How are my goals?"]
    for question in questions:
        await ask(async_client, headers, first["id"], question)

    detail = (await async_client.get(f"/ai/conversations/{first['id']}", headers=headers)).json()
    assert detail["message_count"] == 6
    assert [m["seq"] for m in detail["messages"]] == [1, 2, 3, 4, 5, 6]
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"] * 3
    assert [m["content"] for m in detail["messages"][::2]] == questions
    assert [m["intent"] for m in detail["messages"][1::2]] == [
        "net_worth",
        "recent_expenses",
        "goals",
    ]
    assert detail["title"] == "What's my net worth?"  # set once, by the first question

    latest = (
        await async_client.get(f"/ai/conversations/{first['id']}/messages?limit=2", headers=headers)
    ).json()
    assert [m["seq"] for m in latest] == [5, 6]

    # Asking in the second conversation makes it the most recently active
    await ask(async_client, headers, second["id"], "What's my account balance?")
    listed = (await async_client.get("/ai/conversations", headers=headers)).json()
    assert [(c["id"], c["message_count"]) for c in listed] == [(second["id"], 2), (first["id"], 6)]

    long_question = "Can you tell me " + "a lot about " * 10 + "my spending?"
    assert len(title_from(long_question)) <= 60
    assert title_from(long_question).endswith("…")


@pytest.mark.asyncio
async def test_04_parallel_questions_keep_history_ordered(async_client: httpx.AsyncClient) -> None:
    """Questions sent at the same time each get their own pair of turn numbers."""
    _, headers = await register(async_client, "AI Parallel User")
    conversation = await new_conversation(async_client, headers)

    responses = await asyncio.gather(
        *(
            async_client.post(
                f"/ai/conversations/{conversation['id']}/messages",
                headers=headers,
                json={"content": f"What's my balance? #{n}"},
            )
            for n in range(4)
        )
    )
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    detail = (
        await async_client.get(f"/ai/conversations/{conversation['id']}", headers=headers)
    ).json()
    assert [m["seq"] for m in detail["messages"]] == list(range(1, 9))
    # Each answer directly follows its own question
    for exchange in (r.json() for r in responses):
        assert exchange["assistant_message"]["seq"] == exchange["user_message"]["seq"] + 1


@pytest.mark.asyncio
async def test_05_delete_conversation(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Delete User")
    conversation = await new_conversation(async_client, headers)
    await ask(async_client, headers, conversation["id"], "What's my net worth?")

    deleted = await async_client.delete(f"/ai/conversations/{conversation['id']}", headers=headers)
    assert deleted.status_code == 200
    assert (
        await async_client.get(f"/ai/conversations/{conversation['id']}", headers=headers)
    ).status_code == 404
    async with AsyncSessionLocal() as db:
        left = await db.scalar(
            select(func.count())
            .select_from(AIMessage)
            .where(AIMessage.conversation_id == uuid.UUID(conversation["id"]))
        )
    assert left == 0


# ==============================================================================
# MOCK RESPONSES FROM THE USER'S OWN DATA
# ==============================================================================


@pytest.mark.asyncio
async def test_06_mock_answers_every_topic(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Topics User")
    seeded = await seed_finances(async_client, headers)
    await create(async_client, headers, "/budgets", {"amount": "5000", "month": f"{TODAY:%Y-%m}"})
    await create(
        async_client,
        headers,
        "/goals",
        {
            "name": "MacBook",
            "target_amount": "120000.00",
            "initial_amount": "45000.00",
            "target_date": (TODAY + timedelta(days=200)).isoformat(),
        },
    )
    await create(
        async_client,
        headers,
        "/recurring",
        {
            "title": "Netflix",
            "kind": "subscription",
            "amount": "649.00",
            "account_id": seeded["bank"]["id"],
            "next_due_date": TODAY.isoformat(),
        },
    )
    await create(
        async_client,
        headers,
        "/net-worth/assets",
        {"name": "Gold", "asset_type": "gold", "current_value": "22000.00"},
    )
    await create(
        async_client,
        headers,
        "/net-worth/liabilities",
        {
            "name": "Bike loan",
            "liability_type": "auto_loan",
            "total_amount": "76800",
            "remaining_amount": "38400",
        },
    )

    spending = await answer(async_client, headers, "How much did I spend this month?")
    assert spending["content"] == (
        f"In {THIS_MONTH} you’ve spent ₹1,500 and earned ₹10,000. "
        "You kept ₹8,500, 85% of what you earned. Food1 took the biggest share at ₹1,500 (100%)."
    )
    assert spending["stats"] == [
        {"label": "Spent", "value": "₹1,500"},
        {"label": "Earned", "value": "₹10,000"},
        {"label": "Saved", "value": "₹8,500"},
    ]

    food = await answer(async_client, headers, "How much did I spend on food1?")
    assert food["content"] == (
        f"You’ve spent ₹1,500 on Food1 in {THIS_MONTH} across 2 transactions, "
        "100% of your spending."
    )

    budget = await answer(async_client, headers, "Am I within my budget?")
    assert budget["intent"] == "budget_status"
    assert budget["content"] == (
        f"You’ve used ₹1,500 of your ₹5,000 budget for {THIS_MONTH} (30%), leaving ₹3,500."
    )

    recent = await answer(async_client, headers, "What are my recent expenses?")
    assert recent["intent"] == "recent_expenses"
    assert "Swiggy1 ₹1,000" in recent["content"] and "Zomato1 ₹500" in recent["content"]

    goals = await answer(async_client, headers, "How are my goals doing?")
    assert goals["content"].startswith(
        "You’ve saved ₹45,000 across 1 goal, with ₹75,000 to go. MacBook is at 38%"
    )

    recurring = await answer(async_client, headers, "What subscriptions do I have?")
    assert recurring["intent"] == "recurring"
    assert recurring["content"].startswith(
        f"1 payment totalling ₹649 is due in {THIS_MONTH}. "
        "Subscriptions cost ₹649 a month (₹7,788 a year)."
    )

    worth = await answer(async_client, headers, "What's my net worth?")
    # 50,000 opening - 1,500 spent + 10,000 income + 22,000 gold - 38,400 loan
    assert worth["content"] == (
        "Your net worth is ₹42,100: ₹80,500 in assets minus ₹38,400 in liabilities."
    )

    accounts = await answer(async_client, headers, "What's my account balance?")
    assert accounts["content"] == (
        "Your net balance is ₹58,500 across 1 account. Bank x1 holds the most at ₹58,500."
    )

    unknown = await answer(async_client, headers, "Tell me a joke")
    assert unknown["intent"] == "help"
    assert unknown["content"].startswith("I can answer questions about your own DHAN data")
    assert unknown["stats"] == []


@pytest.mark.asyncio
async def test_07_mock_answers_with_no_data(async_client: httpx.AsyncClient) -> None:
    """A brand-new user gets sensible answers, not errors or someone else's numbers."""
    _, headers = await register(async_client, "AI Empty User")
    expected = {
        "How much did I spend this month?": f"You haven’t recorded any income or spending for {THIS_MONTH} yet.",
        "Show my recent expenses": "You don’t have any expenses recorded yet.",
        "How are my goals?": "You haven’t set any savings goals yet.",
        "Any upcoming bills?": f"You don’t have any recurring payments due in {THIS_MONTH}.",
        "What's my balance?": "You haven’t added any accounts yet.",
        "What's my net worth?": "Your net worth is ₹0: ₹0 in assets minus ₹0 in liabilities.",
    }
    for question, content in expected.items():
        assert (await answer(async_client, headers, question))["content"] == content
    budget = await answer(async_client, headers, "How's my budget?")
    assert budget["content"].startswith(f"You haven’t set a budget for {THIS_MONTH}.")


@pytest.mark.asyncio
async def test_08_mock_provider_templates() -> None:
    """Spec §6 figures read the way the app's canvas reads them."""
    provider = MockProvider()
    september = {
        "month": "September 2026",
        "income": "43000.00",
        "spent": "18640.00",
        "net": "24360.00",
        "savings_rate": 57,
        "expense_count": 38,
        "categories": [
            {"name": "Bills", "amount": "8000.00", "share": "42.9", "count": 10},
            {"name": "Food", "amount": "4200.00", "share": "22.5", "count": 14},
        ],
    }
    reply = await provider.generate(
        ProviderRequest("Where did most of my money go?", Intent.SPENDING_SUMMARY, september)
    )
    assert reply.content == (
        "In September 2026 you’ve spent ₹18,640 and earned ₹43,000. You kept ₹24,360, 57% of "
        "what you earned. Bills took the biggest share at ₹8,000 (42.9%)."
    )
    food = await provider.generate(
        ProviderRequest("How much did I spend on food?", Intent.SPENDING_SUMMARY, september)
    )
    assert food.content == (
        "You’ve spent ₹4,200 on Food in September 2026 across 14 transactions, "
        "22.5% of your spending."
    )

    overspent = await provider.generate(
        ProviderRequest(
            "spending?",
            Intent.SPENDING_SUMMARY,
            {**september, "spent": "50000.00", "net": "-7000.00", "categories": []},
        )
    )
    assert "That’s ₹7,000 more than you earned." in overspent.content
    assert overspent.stats[-1] == Stat("Overspent", "₹7,000")

    over_budget = await provider.generate(
        ProviderRequest(
            "budget?",
            Intent.BUDGET_STATUS,
            {
                "month": "September 2026",
                "limit": "24000.00",
                "spent": "25100.00",
                "remaining": "-1100.00",
                "percentage_used": 104.58,
                "tone": "over",
                "categories": [
                    {
                        "name": "Transport",
                        "limit": "3000",
                        "spent": "2800",
                        "remaining": "200",
                        "percentage_used": 93.33,
                        "tone": "warn",
                    }
                ],
            },
        )
    )
    assert over_budget.content == (
        "You’re ₹1,100 over your ₹24,000 budget for September 2026, with ₹25,100 spent. "
        "Keep an eye on Transport (93%)."
    )

    worth = await provider.generate(
        ProviderRequest(
            "net worth?",
            Intent.NET_WORTH,
            {
                "net_worth": "218680.00",
                "total_assets": "262080.00",
                "total_liabilities": "43400.00",
                "assets": [],
                "liabilities": [],
            },
        )
    )
    assert worth.content == (
        "Your net worth is ₹2,18,680: ₹2,62,080 in assets minus ₹43,400 in liabilities."
    )


# ==============================================================================
# USER ISOLATION AND UNAUTHORIZED ACCESS
# ==============================================================================


@pytest.mark.asyncio
async def test_09_conversations_are_private(async_client: httpx.AsyncClient) -> None:
    _, owner = await register(async_client, "AI Owner")
    _, intruder = await register(async_client, "AI Intruder")
    await seed_finances(async_client, owner, scale=7)
    conversation = await new_conversation(async_client, owner, title="Private")
    await ask(async_client, owner, conversation["id"], "How much did I spend this month?")
    cid = conversation["id"]

    for method, url, body in (
        ("GET", f"/ai/conversations/{cid}", None),
        ("GET", f"/ai/conversations/{cid}/messages", None),
        ("POST", f"/ai/conversations/{cid}/messages", {"content": "What's my balance?"}),
        ("DELETE", f"/ai/conversations/{cid}", None),
    ):
        resp = await async_client.request(method, url, headers=intruder, json=body)
        assert resp.status_code == 404, (method, url)
    assert (await async_client.get("/ai/conversations", headers=intruder)).json() == []

    # The intruder's own questions are answered from the intruder's (empty) data
    theirs = await answer(async_client, intruder, "How much did I spend this month?")
    assert "₹10,500" not in theirs["content"]  # the owner's 1,500 x 7
    assert theirs["content"].startswith("You haven’t recorded any")
    balance = await answer(async_client, intruder, "What's my balance? Show Bank x7 too")
    assert balance["content"] == "You haven’t added any accounts yet."

    # The owner's conversation is untouched
    detail = (await async_client.get(f"/ai/conversations/{cid}", headers=owner)).json()
    assert detail["message_count"] == 2
    assert detail["title"] == "Private"


@pytest.mark.asyncio
async def test_10_provider_only_sees_the_askers_data(
    async_client: httpx.AsyncClient, use_provider
) -> None:
    """What reaches the provider is the asker's data alone, with no user ids, for every topic."""
    owner_user, owner = await register(async_client, "AI Data Owner")
    asker_user, asker = await register(async_client, "AI Data Asker")
    await seed_finances(async_client, owner, scale=9)
    await seed_finances(async_client, asker, scale=2)
    recorder = use_provider(RecordingProvider())

    conversation = await new_conversation(async_client, asker)
    questions = [
        "How much did I spend this month?",
        "Am I within budget?",
        "Recent expenses please",
        "How are my goals?",
        "Upcoming bills?",
        "What's my net worth?",
        "What's my balance?",
    ]
    for question in questions:
        reply = await ask(async_client, asker, conversation["id"], question)
        assert reply["assistant_message"]["provider"] == "recording"

    assert [r.intent for r in recorder.requests] == [
        Intent.SPENDING_SUMMARY,
        Intent.BUDGET_STATUS,
        Intent.RECENT_EXPENSES,
        Intent.GOALS,
        Intent.RECURRING,
        Intent.NET_WORTH,
        Intent.ACCOUNTS,
    ]
    shown = json.dumps([r.facts for r in recorder.requests])
    assert owner_user["id"] not in shown and asker_user["id"] not in shown
    assert "x9" not in shown and "Swiggy9" not in shown and "Food9" not in shown
    assert "13500" not in shown and "90000" not in shown  # the owner's spend and income

    spending = recorder.requests[0].facts
    assert (spending["spent"], spending["income"]) == ("3000.00", "20000.00")
    accounts = recorder.requests[-1].facts
    assert [a["name"] for a in accounts["accounts"]] == ["Bank x2"]
    recent = recorder.requests[2].facts
    assert {e["description"] for e in recent["expenses"]} == {"Swiggy2", "Zomato2"}


@pytest.mark.asyncio
async def test_11_unauthorized_access(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Auth User")
    conversation = await new_conversation(async_client, headers)
    cid = conversation["id"]
    calls = [
        ("GET", "/ai/suggestions", None),
        ("GET", "/ai/conversations", None),
        ("POST", "/ai/conversations", {}),
        ("GET", f"/ai/conversations/{cid}", None),
        ("GET", f"/ai/conversations/{cid}/messages", None),
        ("POST", f"/ai/conversations/{cid}/messages", {"content": "What's my balance?"}),
        ("DELETE", f"/ai/conversations/{cid}", None),
    ]
    for auth in (None, {"Authorization": "Bearer not-a-real-token"}):
        for method, url, body in calls:
            resp = await async_client.request(method, url, headers=auth, json=body)
            assert resp.status_code == 401, (auth, method, url)

    detail = (await async_client.get(f"/ai/conversations/{cid}", headers=headers)).json()
    assert detail["message_count"] == 0


@pytest.mark.asyncio
async def test_12_validation(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Validation User")
    conversation = await new_conversation(async_client, headers)
    url = f"/ai/conversations/{conversation['id']}/messages"
    for body in ({"content": ""}, {"content": "   \n "}, {"content": "x" * 2001}, {}):
        assert (await async_client.post(url, headers=headers, json=body)).status_code == 422
    assert (
        await async_client.get("/ai/conversations/not-a-uuid", headers=headers)
    ).status_code == 422
    assert (
        await async_client.post(
            f"/ai/conversations/{uuid.uuid4()}/messages",
            headers=headers,
            json={"content": "hi"},
        )
    ).status_code == 404
    for bad_limit in (0, 501):
        assert (
            await async_client.get(
                f"/ai/conversations/{conversation['id']}?limit={bad_limit}", headers=headers
            )
        ).status_code == 422


# ==============================================================================
# PROVIDER ABSTRACTION
# ==============================================================================


@pytest.mark.asyncio
async def test_13_provider_failure_saves_nothing(
    async_client: httpx.AsyncClient, use_provider
) -> None:
    _, headers = await register(async_client, "AI Failure User")
    conversation = await new_conversation(async_client, headers)
    use_provider(FailingProvider())

    resp = await async_client.post(
        f"/ai/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"content": "What's my net worth?"},
    )
    assert resp.status_code == 503
    assert "try again" in resp.json()["detail"]
    assert "upstream" not in resp.json()["detail"]  # internals aren't leaked
    detail = (
        await async_client.get(f"/ai/conversations/{conversation['id']}", headers=headers)
    ).json()
    assert (detail["message_count"], detail["title"]) == (0, "")


@pytest.mark.asyncio
async def test_14_unconfigured_provider_is_refused(
    async_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Naming a provider that isn't registered never silently calls anything."""
    _, headers = await register(async_client, "AI Config User")
    conversation = await new_conversation(async_client, headers)
    monkeypatch.setattr(settings, "AI_PROVIDER", "some-paid-llm")

    resp = await async_client.post(
        f"/ai/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"content": "What's my net worth?"},
    )
    assert resp.status_code == 503
    assert "some-paid-llm" in resp.json()["detail"]
    # Reading history doesn't need a provider
    assert (await async_client.get("/ai/conversations", headers=headers)).status_code == 200
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    assert (await ask(async_client, headers, conversation["id"], "What's my net worth?"))[
        "assistant_message"
    ]["provider"] == "mock"


@pytest.mark.asyncio
async def test_15_history_given_to_provider(
    async_client: httpx.AsyncClient, use_provider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The provider gets this conversation's latest turns, never another conversation's."""
    _, headers = await register(async_client, "AI Context User")
    recorder = use_provider(RecordingProvider())
    monkeypatch.setattr(settings, "AI_HISTORY_LIMIT", 3)
    first = await new_conversation(async_client, headers)
    other = await new_conversation(async_client, headers)

    await ask(async_client, headers, first["id"], "What's my net worth?")
    await ask(async_client, headers, other["id"], "Secret question elsewhere")
    await ask(async_client, headers, first["id"], "And my balance?")
    await ask(async_client, headers, first["id"], "Recent expenses?")

    assert recorder.requests[0].history == []
    assert recorder.requests[1].history == []  # a new conversation starts clean
    second_turn = recorder.requests[2].history
    assert [(t.role, t.content) for t in second_turn] == [
        ("user", "What's my net worth?"),
        ("assistant", "Recorded #1"),
    ]
    third_turn = recorder.requests[3].history
    assert [t.content for t in third_turn] == ["Recorded #1", "And my balance?", "Recorded #3"]
    assert all("Secret" not in t.content for r in recorder.requests for t in r.history)


@pytest.mark.asyncio
async def test_16_conversation_deleted_while_answering(
    async_client: httpx.AsyncClient, use_provider
) -> None:
    """If the conversation disappears mid-answer, nothing is written and the client gets 404."""
    _, headers = await register(async_client, "AI Race User")
    conversation = await new_conversation(async_client, headers)

    class DeletingProvider(AIProvider):
        name = "deleting"

        async def generate(self, request: ProviderRequest) -> ProviderReply:
            async with AsyncSessionLocal() as other:
                found = await other.get(AIConversation, uuid.UUID(conversation["id"]))
                await other.delete(found)
                await other.commit()
            return ProviderReply(content="too late")

    use_provider(DeletingProvider())
    resp = await async_client.post(
        f"/ai/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"content": "What's my balance?"},
    )
    assert resp.status_code == 404
    async with AsyncSessionLocal() as db:
        orphans = await db.scalar(
            select(func.count())
            .select_from(AIMessage)
            .where(AIMessage.conversation_id == uuid.UUID(conversation["id"]))
        )
    assert orphans == 0


@pytest.mark.asyncio
async def test_17_suggestions_and_versioned_routes(async_client: httpx.AsyncClient) -> None:
    _, headers = await register(async_client, "AI Routes User")
    suggestions = (await async_client.get("/ai/suggestions", headers=headers)).json()["suggestions"]
    assert len(suggestions) == 8
    # Every suggestion is a question DHAN AI understands
    assert all(classify(s) is not Intent.HELP for s in suggestions)

    created = await async_client.post("/api/v1/ai/conversations", headers=headers)
    assert created.status_code == 201
    exchange = await async_client.post(
        f"/api/v1/ai/conversations/{created.json()['id']}/messages",
        headers=headers,
        json={"content": "What's my net worth?"},
    )
    assert exchange.status_code == 201


# ==============================================================================
# UNDERSTANDING QUESTIONS
# ==============================================================================


def test_18_intent_classification() -> None:
    cases = {
        "How much did I spend on food this month?": Intent.SPENDING_SUMMARY,
        "Where did most of my money go?": Intent.SPENDING_SUMMARY,
        "How much did I save in September?": Intent.SPENDING_SUMMARY,
        "Am I over budget?": Intent.BUDGET_STATUS,
        "Did I overspend?": Intent.BUDGET_STATUS,
        "Show my latest transactions": Intent.RECENT_EXPENSES,
        "How are my savings goals?": Intent.GOALS,
        "Which bills are due this week?": Intent.RECURRING,
        "List my subscriptions": Intent.RECURRING,
        "When is my next EMI?": Intent.RECURRING,
        "What's my net worth?": Intent.NET_WORTH,
        "How much do I owe on my loan?": Intent.NET_WORTH,
        "What's my account balance?": Intent.ACCOUNTS,
        "How much is in my wallet?": Intent.ACCOUNTS,
        "What's the weather?": Intent.HELP,
        "What bills are coming up?": Intent.RECURRING,
        "Is YouTube Premium worth it?": Intent.HELP,  # "worth" alone isn't net worth
        "Premium plans": Intent.HELP,  # "emi" only matches at a word start
    }
    for question, intent in cases.items():
        assert classify(question) is intent, question


def test_19_month_resolution() -> None:
    today = date(2026, 10, 4)
    assert resolve_month("How much did I spend?", today) == (2026, 10)
    assert resolve_month("spending last month", today) == (2026, 9)
    assert resolve_month("spend in September", today) == (2026, 9)
    assert resolve_month("spend in Sept", today) == (2026, 9)
    assert resolve_month("what about december", today) == (2025, 12)  # the one just gone
    assert resolve_month("May I see my spending?", today) == (2026, 10)
    assert resolve_month("spending in may", today) == (2026, 5)
    assert resolve_month("last month", date(2027, 1, 15)) == (2026, 12)
