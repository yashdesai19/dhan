"""Works out what a DHAN AI question is about, and which month it means.

Keyword rules: cheap, deterministic, and enough for the questions DHAN supports. The intent
decides which slice of the user's data is fetched, so a question never pulls more than it needs.
"""

import re
from datetime import date
from enum import StrEnum

from fastapi_app.core.periods import shift_month


class Intent(StrEnum):
    SPENDING_SUMMARY = "spending_summary"
    BUDGET_STATUS = "budget_status"
    RECENT_EXPENSES = "recent_expenses"
    GOALS = "goals"
    RECURRING = "recurring"
    NET_WORTH = "net_worth"
    ACCOUNTS = "accounts"
    SPLITS = "splits"
    HELP = "help"


# First match wins, so more specific topics come before broader ones
# ("budget" before "spend", "net worth" before "balance").
_RULES: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.NET_WORTH, ("net worth", "networth", "assets", "liabilit", "loan", "debt")),
    (Intent.SPLITS, ("owe", "split", "settle", "group", "lent", "friends")),
    (Intent.BUDGET_STATUS, ("budget", "limit", "overspen", "over spen")),
    (
        Intent.RECURRING,
        ("recurring", "subscription", "upcoming", "coming up", "due", "emi", "repeat"),
    ),
    (Intent.GOALS, ("goal", "saving for", "target")),
    (
        Intent.RECENT_EXPENSES,
        ("recent", "latest", "last few", "last expense", "transactions", "history"),
    ),
    (Intent.ACCOUNTS, ("account", "balance", "bank", "wallet", "cash in hand")),
    (
        Intent.SPENDING_SUMMARY,
        (
            "spend",
            "spent",
            "spending",
            "expense",
            "money go",
            "save",
            "saved",
            "saving",
            "earn",
            "income",
            "cost",
        ),
    ),
]

_MONTHS = {
    name: index
    for index, names in enumerate(
        (
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sept", "sep"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ),
        start=1,
    )
    for name in names
}


# Keywords match from the start of a word: "emi" finds "EMIs" but not "premium"
_PATTERNS = [
    (intent, re.compile("|".join(rf"\b{re.escape(k)}" for k in keywords)))
    for intent, keywords in _RULES
]


def classify(question: str) -> Intent:
    """The topic of a question, or HELP when it isn't one DHAN AI answers."""
    text = question.lower()
    for intent, pattern in _PATTERNS:
        if pattern.search(text):
            return intent
    return Intent.HELP


def resolve_month(question: str, today: date) -> tuple[int, int]:
    """The month a question refers to: 'last month', a month name, or else the current one.

    A named month later in the year than today means last year's ("in December", asked in
    October, is the December just gone).
    """
    text = question.lower()
    if "last month" in text or "previous month" in text:
        return shift_month(today.year, today.month, -1)
    for position, word in enumerate(re.findall(r"[a-z]+", text)):
        if word == "may" and position == 0:
            continue  # "May I see ...?"
        month = _MONTHS.get(word)
        if month is not None:
            year = today.year if month <= today.month else today.year - 1
            return year, month
    return today.year, today.month
