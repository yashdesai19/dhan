"""FastAPI endpoints for DHAN Budgets."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.budget import (
    BudgetCreate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetUpdate,
    CategoryBudgetCreate,
)
from fastapi_app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("", response_model=list[BudgetResponse])
@router.get("/", response_model=list[BudgetResponse], include_in_schema=False)
async def list_budgets(
    response: Response,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: str | None = Query(default=None, description="Filter by month in YYYY-MM format"),
    category_id: uuid.UUID | None = Query(default=None, description="Filter by category ID"),
    period: str | None = Query(
        default=None, description="Filter by periodicity (monthly, weekly, yearly)"
    ),
    start_date: date | None = Query(
        default=None, description="Filter budgets starting on/after date"
    ),
    end_date: date | None = Query(default=None, description="Filter budgets ending on/before date"),
) -> list[BudgetResponse]:
    """List all budgets configured for the authenticated user with dynamic spending metrics."""
    items = await budget_service.list_budgets(
        db=db,
        user_id=current_user.id,
        month=month,
        category_id=category_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )
    response.headers["X-Total-Count"] = str(len(items))
    return items


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
async def create_budget(
    payload: BudgetCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    """Create a new monthly or category-specific budget ceiling."""
    return await budget_service.create_budget(
        db=db,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: str | None = Query(default=None, description="Target month in YYYY-MM format"),
) -> BudgetSummaryResponse:
    """Get aggregated monthly budget summary and category breakdown."""
    return await budget_service.get_budget_summary(
        db=db,
        user_id=current_user.id,
        month=month,
    )


@router.post("/category", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def set_category_budget(
    payload: CategoryBudgetCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    """Dedicated endpoint to configure a budget ceiling for a specific category."""
    budget_data = BudgetCreate(
        category_id=payload.category_id,
        amount=payload.amount,
        month=payload.month,
        warn_at_percent=payload.warn_at_percent,
        rollover=payload.rollover,
    )
    return await budget_service.create_budget(
        db=db,
        user_id=current_user.id,
        data=budget_data,
    )


@router.get("/category/{category_id}", response_model=BudgetResponse)
async def get_category_budget(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: str | None = Query(default=None, description="Month in YYYY-MM format"),
) -> BudgetResponse:
    """Retrieve budget status for a single category in a specific month."""
    items = await budget_service.list_budgets(
        db=db,
        user_id=current_user.id,
        month=month,
        category_id=category_id,
    )
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No budget found for category '{category_id}' in month '{month or 'current'}'.",
        )
    return items[0]


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    """Retrieve an individual budget by ID with on-the-fly calculated spending totals."""
    return await budget_service.get_budget_by_id(
        db=db,
        user_id=current_user.id,
        budget_id=budget_id,
    )


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetResponse:
    """Update a budget ceiling or configuration parameters."""
    return await budget_service.update_budget(
        db=db,
        user_id=current_user.id,
        budget_id=budget_id,
        data=payload,
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a budget configuration."""
    await budget_service.delete_budget(
        db=db,
        user_id=current_user.id,
        budget_id=budget_id,
    )
