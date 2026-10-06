"""API v1 endpoints."""

from fastapi_app.api.v1.endpoints import (
    accounts,
    auth,
    budgets,
    categories,
    goals,
    health,
    recurring,
    splits,
    transactions,
)

__all__ = [
    "auth",
    "health",
    "accounts",
    "categories",
    "transactions",
    "budgets",
    "splits",
    "goals",
    "recurring",
]
