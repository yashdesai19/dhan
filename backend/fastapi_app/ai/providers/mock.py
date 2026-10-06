"""Free, deterministic provider: templated answers built only from the facts it is handed."""

import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi_app.ai.intents import Intent
from fastapi_app.ai.providers.base import AIProvider, ProviderReply, ProviderRequest, Stat
from fastapi_app.core.money import format_inr

HELP_TEXT = (
    "I can answer questions about your own DHAN data: spending, budget, recent expenses, "
    "goals, recurring payments, net worth, accounts and splits. Try “How much did I spend this month?”"
)


def _inr(value: str) -> str:
    return format_inr(Decimal(value))


def _day(iso: str) -> str:
    """'2026-09-30' -> '30 Sep'."""
    return date.fromisoformat(iso).strftime("%d %b").lstrip("0")


def _pct(value: Any) -> str:
    """42.9 -> '42.9%', 57 -> '57%'."""
    number = Decimal(str(value)).normalize()
    return f"{number:f}%"


def _mentions(question: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name.lower())}\b", question.lower()) is not None


class MockProvider(AIProvider):
    name = "mock"

    async def generate(self, request: ProviderRequest) -> ProviderReply:
        facts = request.facts
        match request.intent:
            case Intent.SPENDING_SUMMARY:
                return self._spending(request.question, facts)
            case Intent.BUDGET_STATUS:
                return self._budget(facts)
            case Intent.RECENT_EXPENSES:
                return self._recent(facts)
            case Intent.GOALS:
                return self._goals(facts)
            case Intent.RECURRING:
                return self._recurring(facts)
            case Intent.NET_WORTH:
                return self._net_worth(facts)
            case Intent.ACCOUNTS:
                return self._accounts(facts)
            case Intent.SPLITS:
                return self._splits(facts)
            case _:
                return ProviderReply(content=HELP_TEXT)

    def _spending(self, question: str, f: dict[str, Any]) -> ProviderReply:
        month = f["month"]
        categories = f["categories"]
        asked = next((c for c in categories if _mentions(question, c["name"])), None)
        if asked:
            count = asked["count"]
            return ProviderReply(
                content=(
                    f"You’ve spent {_inr(asked['amount'])} on {asked['name']} in {month} "
                    f"across {count} transaction{'s' if count != 1 else ''}, "
                    f"{_pct(asked['share'])} of your spending."
                ),
                stats=[
                    Stat(f"{asked['name']} spent", _inr(asked["amount"])),
                    Stat("Share", _pct(asked["share"])),
                    Stat("Transactions", str(count)),
                ],
            )

        spent, income, net = Decimal(f["spent"]), Decimal(f["income"]), Decimal(f["net"])
        if spent == 0 and income == 0:
            return ProviderReply(
                content=f"You haven’t recorded any income or spending for {month} yet."
            )
        parts = [f"In {month} you’ve spent {_inr(f['spent'])} and earned {_inr(f['income'])}."]
        if net >= 0 and income > 0:
            parts.append(f"You kept {_inr(f['net'])}, {f['savings_rate']}% of what you earned.")
        elif net < 0:
            parts.append(f"That’s {format_inr(-net)} more than you earned.")
        if categories:
            top = categories[0]
            parts.append(
                f"{top['name']} took the biggest share at {_inr(top['amount'])} "
                f"({_pct(top['share'])})."
            )
        return ProviderReply(
            content=" ".join(parts),
            stats=[
                Stat("Spent", _inr(f["spent"])),
                Stat("Earned", _inr(f["income"])),
                Stat("Saved" if net >= 0 else "Overspent", format_inr(abs(net))),
            ],
        )

    def _budget(self, f: dict[str, Any]) -> ProviderReply:
        month = f["month"]
        if Decimal(f["limit"]) == 0:
            return ProviderReply(
                content=(
                    f"You haven’t set a budget for {month}. You’ve spent "
                    f"{_inr(f['spent'])} so far; setting one lets me track it for you."
                ),
                stats=[Stat("Spent", _inr(f["spent"]))],
            )
        remaining = Decimal(f["remaining"])
        if remaining >= 0:
            content = (
                f"You’ve used {_inr(f['spent'])} of your {_inr(f['limit'])} budget for {month} "
                f"({round(f['percentage_used'])}%), leaving {_inr(f['remaining'])}."
            )
        else:
            content = (
                f"You’re {format_inr(-remaining)} over your {_inr(f['limit'])} budget for "
                f"{month}, with {_inr(f['spent'])} spent."
            )
        watch = [c for c in f["categories"] if c["tone"] in ("warn", "over")]
        if watch:
            names = ", ".join(f"{c['name']} ({round(c['percentage_used'])}%)" for c in watch)
            content += f" Keep an eye on {names}."
        return ProviderReply(
            content=content,
            stats=[
                Stat("Spent", _inr(f["spent"])),
                Stat("Budget", _inr(f["limit"])),
                Stat("Left" if remaining >= 0 else "Over", format_inr(abs(remaining))),
            ],
        )

    def _recent(self, f: dict[str, Any]) -> ProviderReply:
        expenses = f["expenses"]
        if not expenses:
            return ProviderReply(content="You don’t have any expenses recorded yet.")
        listed = ", ".join(
            f"{e['description']} {_inr(e['amount'])} ({_day(e['date'])})" for e in expenses
        )
        return ProviderReply(
            content=f"Your latest expenses: {listed}.",
            stats=[Stat(e["description"], _inr(e["amount"])) for e in expenses[:3]],
        )

    def _goals(self, f: dict[str, Any]) -> ProviderReply:
        if f["count"] == 0:
            return ProviderReply(content="You haven’t set any savings goals yet.")
        goals = "; ".join(f"{g['name']} is at {g['pct']}% ({g['pill']})" for g in f["goals"])
        count = f["count"]
        return ProviderReply(
            content=(
                f"You’ve saved {_inr(f['total_saved'])} across {count} "
                f"goal{'s' if count != 1 else ''}, with {_inr(f['total_left'])} to go. {goals}."
            ),
            stats=[
                Stat("Saved", _inr(f["total_saved"])),
                Stat("To go", _inr(f["total_left"])),
                Stat("Goals", str(count)),
            ],
        )

    def _recurring(self, f: dict[str, Any]) -> ProviderReply:
        if f["outgoing_count"] == 0 and f["subscriptions_count"] == 0:
            return ProviderReply(
                content=f"You don’t have any recurring payments due in {f['month']}."
            )
        count = f["outgoing_count"]
        parts = [
            f"{count} payment{'s' if count != 1 else ''} totalling "
            f"{_inr(f['outgoing_total'])} {'are' if count != 1 else 'is'} due in {f['month']}."
        ]
        if f["subscriptions_count"]:
            parts.append(
                f"Subscriptions cost {_inr(f['subscriptions_monthly'])} a month "
                f"({_inr(f['subscriptions_yearly'])} a year)."
            )
        if f["next_7_days"]:
            soon = ", ".join(
                f"{p['title']} {_inr(p['amount'])} on {_day(p['due'])}" for p in f["next_7_days"]
            )
            parts.append(f"Coming up in the next 7 days: {soon}.")
        return ProviderReply(
            content=" ".join(parts),
            stats=[
                Stat("Due this month", _inr(f["outgoing_total"])),
                Stat("Subscriptions", f"{_inr(f['subscriptions_monthly'])}/mo"),
                Stat("Next 7 days", _inr(f["next_7_days_total"])),
            ],
        )

    def _net_worth(self, f: dict[str, Any]) -> ProviderReply:
        return ProviderReply(
            content=(
                f"Your net worth is {_inr(f['net_worth'])}: {_inr(f['total_assets'])} in assets "
                f"minus {_inr(f['total_liabilities'])} in liabilities."
            ),
            stats=[
                Stat("Assets", _inr(f["total_assets"])),
                Stat("Liabilities", _inr(f["total_liabilities"])),
                Stat("Net worth", _inr(f["net_worth"])),
            ],
        )

    def _accounts(self, f: dict[str, Any]) -> ProviderReply:
        accounts = f["accounts"]
        if not accounts:
            return ProviderReply(content="You haven’t added any accounts yet.")
        count = f["counted_accounts"]
        largest = max(accounts, key=lambda a: Decimal(a["balance"]))
        return ProviderReply(
            content=(
                f"Your net balance is {_inr(f['net_balance'])} across {count} "
                f"account{'s' if count != 1 else ''}. {largest['name']} holds the most at "
                f"{_inr(largest['balance'])}."
            ),
            stats=[
                Stat(a["name"], _inr(a["balance"]))
                for a in sorted(accounts, key=lambda a: -Decimal(a["balance"]))[:3]
            ],
        )

    def _splits(self, f: dict[str, Any]) -> ProviderReply:
        people = f["people"]
        if not people:
            return ProviderReply(content="You’re all square: nobody owes you and you owe nobody.")
        owed = [p for p in people if Decimal(p["balance"]) > 0]
        owing = [p for p in people if Decimal(p["balance"]) < 0]
        parts = []
        if owed:
            names = ", ".join(f"{p['name']} {_inr(p['balance'])}" for p in owed)
            parts.append(f"You’re owed {_inr(f['owed'])} ({names}).")
        if owing:
            names = ", ".join(f"{p['name']} {_inr(str(-Decimal(p['balance'])))}" for p in owing)
            parts.append(f"You owe {_inr(f['owe'])} ({names}).")
        return ProviderReply(
            content=" ".join(parts),
            stats=[
                Stat("You’re owed", _inr(f["owed"])),
                Stat("You owe", _inr(f["owe"])),
                Stat("Net", _inr(f["net"])),
            ],
        )
