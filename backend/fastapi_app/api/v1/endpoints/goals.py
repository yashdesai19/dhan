"""API Router for DHAN Goals and Contributions."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import get_current_user, get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.goal import (
    GoalContributionCreate,
    GoalContributionResponse,
    GoalCreate,
    GoalResponse,
    GoalsSummaryResponse,
    GoalUpdate,
)
from fastapi_app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["Goals"])

AS_OF_DESCRIPTION = "Client's local date for time-based progress (defaults to server date)"


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
async def create_goal(
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Create a new savings goal target."""
    return await GoalService.create_goal(db=db, user_id=current_user.id, goal_in=goal_in)


@router.get("", response_model=list[GoalResponse])
@router.get("/", response_model=list[GoalResponse], include_in_schema=False)
async def list_goals(
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status e.g. in_progress, achieved"
    ),
    as_of: date | None = Query(None, description=AS_OF_DESCRIPTION),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GoalResponse]:
    """Retrieve all savings goals owned by authenticated user."""
    return await GoalService.list_goals(
        db=db, user_id=current_user.id, status_filter=status_filter, as_of_date=as_of
    )


@router.get("/totals", response_model=GoalsSummaryResponse)
async def get_goals_totals(
    as_of: date | None = Query(None, description=AS_OF_DESCRIPTION),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalsSummaryResponse:
    """Get aggregated metrics (total saved, total left, total target, count) across user goals."""
    return await GoalService.get_goals_totals(db=db, user_id=current_user.id, as_of_date=as_of)


@router.get("/{id}", response_model=GoalResponse)
async def get_goal(
    id: uuid.UUID,
    as_of: date | None = Query(None, description=AS_OF_DESCRIPTION),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Retrieve details, progress indicators, and contribution ledger for a specific goal."""
    return await GoalService.get_goal(db=db, user_id=current_user.id, goal_id=id, as_of_date=as_of)


@router.patch("/{id}", response_model=GoalResponse)
async def update_goal(
    id: uuid.UUID,
    update_in: GoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Update goal parameters (name, target_amount, deadline date, icon, status)."""
    return await GoalService.update_goal(
        db=db, user_id=current_user.id, goal_id=id, update_in=update_in
    )


@router.delete("/{id}", response_model=dict[str, str])
async def delete_goal(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a savings goal and all associated contribution records."""
    return await GoalService.delete_goal(db=db, user_id=current_user.id, goal_id=id)


@router.post("/{id}/contributions", response_model=GoalResponse)
@router.post("/{id}/add-money", response_model=GoalResponse, include_in_schema=False)
async def add_money(
    id: uuid.UUID,
    contrib_in: GoalContributionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Deposit money towards a goal target."""
    return await GoalService.add_money(
        db=db, user_id=current_user.id, goal_id=id, contrib_in=contrib_in
    )


@router.get("/{id}/contributions", response_model=list[GoalContributionResponse])
async def list_contributions(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GoalContributionResponse]:
    """List contribution history for a specific goal."""
    goal_res = await GoalService.get_goal(db=db, user_id=current_user.id, goal_id=id)
    return goal_res.contributions


@router.delete("/{id}/contributions/{contribution_id}", response_model=GoalResponse)
async def remove_contribution(
    id: uuid.UUID,
    contribution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    """Undo a contribution, taking its amount back off the goal."""
    return await GoalService.remove_contribution(
        db=db, user_id=current_user.id, goal_id=id, contribution_id=contribution_id
    )
