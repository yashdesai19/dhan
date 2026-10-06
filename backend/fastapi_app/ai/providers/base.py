"""The contract every DHAN AI provider implements.

A provider turns a question plus a bundle of facts into an answer. It never touches the
database and is never told who the user is: AIService fetches the facts for the authenticated
user before calling it, so swapping the mock for a hosted model can't widen what the model sees.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from fastapi_app.ai.intents import Intent


@dataclass(frozen=True)
class Stat:
    """A highlighted figure shown under an answer, e.g. Spent / ₹18,640."""

    label: str
    value: str


@dataclass(frozen=True)
class HistoryTurn:
    role: str  # user | assistant
    content: str


@dataclass(frozen=True)
class ProviderRequest:
    question: str
    intent: Intent
    # JSON-safe snapshot of the authenticated user's own data for this intent (money as
    # strings, no user ids). Empty for HELP.
    facts: dict[str, Any]
    history: list[HistoryTurn] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderReply:
    content: str
    stats: list[Stat] = field(default_factory=list)


class AIProvider(ABC):
    """Generates an answer. Implementations must answer only from request.facts."""

    name: str

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderReply:
        """Raise any exception to signal the provider is unavailable; nothing is saved then."""


class AIProviderUnavailable(Exception):
    """The configured provider can't be used (not registered, misconfigured, or down)."""
