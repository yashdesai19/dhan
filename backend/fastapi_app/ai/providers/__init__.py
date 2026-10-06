"""Provider registry. Adding a hosted model later means registering it here and setting
AI_PROVIDER; nothing else in the request path changes."""

from collections.abc import Callable

from fastapi_app.ai.providers.base import (
    AIProvider,
    AIProviderUnavailable,
    HistoryTurn,
    ProviderReply,
    ProviderRequest,
    Stat,
)
from fastapi_app.ai.providers.mock import MockProvider
from fastapi_app.core.config import settings

PROVIDERS: dict[str, Callable[[], AIProvider]] = {
    "mock": MockProvider,
}


def get_ai_provider() -> AIProvider:
    """The configured provider (FastAPI dependency; tests override it)."""
    factory = PROVIDERS.get(settings.AI_PROVIDER)
    if factory is None:
        raise AIProviderUnavailable(f"AI provider {settings.AI_PROVIDER!r} is not available.")
    return factory()


__all__ = [
    "PROVIDERS",
    "AIProvider",
    "AIProviderUnavailable",
    "HistoryTurn",
    "MockProvider",
    "ProviderReply",
    "ProviderRequest",
    "Stat",
    "get_ai_provider",
]
