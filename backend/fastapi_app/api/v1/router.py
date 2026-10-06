"""API v1 master router."""

from fastapi import APIRouter

from fastapi_app.api.v1.endpoints import (
    accounts,
    ai,
    auth,
    budgets,
    categories,
    goals,
    health,
    net_worth,
    recurring,
    reports,
    splits,
    transactions,
)

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(accounts.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(transactions.router)
api_v1_router.include_router(budgets.router)
api_v1_router.include_router(splits.groups_router)
api_v1_router.include_router(splits.splits_router)
api_v1_router.include_router(splits.settlements_router)
api_v1_router.include_router(splits.people_router)
api_v1_router.include_router(goals.router)
api_v1_router.include_router(recurring.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(net_worth.router)
api_v1_router.include_router(ai.router)

__all__ = ["api_v1_router"]
