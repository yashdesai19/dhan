"""Service layer for DHAN Goals and Goal Contributions."""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.money import format_inr
from fastapi_app.models.account import Account
from fastapi_app.models.goal import Goal, GoalContribution
from fastapi_app.schemas.goal import (
    GoalContributionCreate,
    GoalContributionResponse,
    GoalCreate,
    GoalProgressResponse,
    GoalResponse,
    GoalsSummaryResponse,
    GoalUpdate,
)

ZERO = Decimal("0.00")


def _round_half_up(value: Decimal) -> int:
    """Rounds to a whole number with halves going up, like the app's Math.round."""
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_goal_progress(goal: Goal, as_of_date: date | None = None) -> GoalProgressResponse:
    """Computes progress metrics according to DHAN specification §6 (mirrors utils/goals.ts)."""
    today = as_of_date or date.today()
    saved = goal.current_amount
    left = max(ZERO, goal.target_amount - saved)

    # Integer percentage
    pct = _round_half_up(saved / goal.target_amount * 100) if goal.target_amount > 0 else 0

    # Months until target date (calendar month difference)
    months_diff = (goal.target_date.year - today.year) * 12 + (goal.target_date.month - today.month)
    months_left = max(1, months_diff)

    # Monthly amount needed, in whole rupees
    monthly = Decimal(_round_half_up(left / months_left))

    # Timeline calculation
    created_date = (
        goal.created_at.date() if isinstance(goal.created_at, datetime) else goal.created_at
    )
    span_days = max(1, (goal.target_date - created_date).days)
    elapsed_days = min(span_days, max(0, (today - created_date).days))
    expected = (goal.target_amount * Decimal(elapsed_days)) / Decimal(span_days)

    if left <= ZERO:
        prog_status = "done"
        pill = "Done"
    elif saved >= expected:
        prog_status = "onTrack"
        pill = "On track" if pct >= 50 else f"{format_inr(monthly)}/mo"
    else:
        prog_status = "behind"
        pill = "Behind"

    return GoalProgressResponse(
        saved=saved,
        left=left,
        pct=pct,
        months_left=months_left,
        monthly=monthly,
        status=prog_status,
        pill=pill,
    )


def _sync_completion_status(goal: Goal) -> None:
    """Keeps in_progress/achieved in step with the saved amount; paused/cancelled are left alone."""
    if goal.status in ("in_progress", "achieved"):
        goal.status = "achieved" if goal.current_amount >= goal.target_amount else "in_progress"


async def _get_owned_goal(
    db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID, *, for_update: bool = False
) -> Goal:
    """Loads a goal owned by the user (row-locked when for_update), else 404."""
    stmt = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    goal = (await db.execute(stmt)).scalar_one_or_none()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found or access denied.",
        )
    return goal


async def _ensure_account_owned(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID | None
) -> None:
    """404s unless account_id is empty or belongs to the user."""
    if account_id is None:
        return
    stmt = select(Account.id).where(Account.id == account_id, Account.user_id == user_id)
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied.",
        )


async def _contributions_by_goal(
    db: AsyncSession, goal_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[GoalContribution]]:
    """Fetches contributions for several goals in one query, newest first."""
    grouped: dict[uuid.UUID, list[GoalContribution]] = defaultdict(list)
    if not goal_ids:
        return grouped
    stmt = (
        select(GoalContribution)
        .where(GoalContribution.goal_id.in_(goal_ids))
        .order_by(GoalContribution.date.desc(), GoalContribution.created_at.desc())
    )
    for contribution in (await db.execute(stmt)).scalars():
        grouped[contribution.goal_id].append(contribution)
    return grouped


def _to_response(
    goal: Goal, contributions: list[GoalContribution], as_of_date: date | None
) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        icon=goal.icon,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        status=goal.status,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
        progress=calculate_goal_progress(goal, as_of_date),
        contributions=[GoalContributionResponse.model_validate(c) for c in contributions],
    )


class GoalService:
    """Handles business logic and data persistence for Goals and Contributions.

    Contributions are earmarks against a goal: they never create ledger transactions or move
    account balances (the app's goalsRepo.addContribution behaves the same way).
    """

    @staticmethod
    async def create_goal(
        db: AsyncSession, user_id: uuid.UUID, goal_in: GoalCreate
    ) -> GoalResponse:
        """Creates a new goal, optionally recording an initial deposit."""
        if goal_in.target_amount <= ZERO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target amount must be greater than zero.",
            )

        if goal_in.initial_amount < ZERO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial amount cannot be negative.",
            )

        await _ensure_account_owned(db, user_id, goal_in.account_id)

        goal = Goal(
            user_id=user_id,
            name=goal_in.name,
            icon=goal_in.icon,
            target_amount=goal_in.target_amount,
            current_amount=goal_in.initial_amount,
            target_date=goal_in.target_date,
            status="achieved" if goal_in.initial_amount >= goal_in.target_amount else "in_progress",
            created_at=goal_in.created_at or datetime.now(UTC),
        )
        db.add(goal)
        await db.flush()

        # If initial contribution given, persist contribution record
        if goal_in.initial_amount > ZERO:
            db.add(
                GoalContribution(
                    goal_id=goal.id,
                    user_id=user_id,
                    account_id=goal_in.account_id,
                    amount=goal_in.initial_amount,
                    date=date.today(),
                    notes="Initial deposit upon goal creation",
                )
            )

        await db.commit()
        return await GoalService.get_goal(db, user_id, goal.id)

    @staticmethod
    async def get_goal(
        db: AsyncSession,
        user_id: uuid.UUID,
        goal_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> GoalResponse:
        """Retrieves a single goal owned by user with progress and contributions."""
        goal = await _get_owned_goal(db, user_id, goal_id)
        contributions = await _contributions_by_goal(db, [goal.id])
        return _to_response(goal, contributions[goal.id], as_of_date)

    @staticmethod
    async def list_goals(
        db: AsyncSession,
        user_id: uuid.UUID,
        status_filter: str | None = None,
        as_of_date: date | None = None,
    ) -> list[GoalResponse]:
        """Lists user goals with calculated progress."""
        query = select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
        if status_filter:
            query = query.where(Goal.status == status_filter)

        goals = (await db.execute(query)).scalars().all()
        contributions = await _contributions_by_goal(db, [g.id for g in goals])
        return [_to_response(g, contributions[g.id], as_of_date) for g in goals]

    @staticmethod
    async def update_goal(
        db: AsyncSession,
        user_id: uuid.UUID,
        goal_id: uuid.UUID,
        update_in: GoalUpdate,
    ) -> GoalResponse:
        """Updates goal parameters and reconciles status."""
        goal = await _get_owned_goal(db, user_id, goal_id, for_update=True)

        new_target = update_in.target_amount or goal.target_amount
        if update_in.status == "achieved" and goal.current_amount < new_target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A goal can only be marked achieved once its target is reached.",
            )

        if update_in.name is not None:
            goal.name = update_in.name
        if update_in.icon is not None:
            goal.icon = update_in.icon
        if update_in.target_date is not None:
            goal.target_date = update_in.target_date
        if update_in.created_at is not None:
            goal.created_at = update_in.created_at
        if update_in.target_amount is not None:
            goal.target_amount = update_in.target_amount
        if update_in.status is not None:
            goal.status = update_in.status
        _sync_completion_status(goal)

        goal.updated_at = datetime.now(UTC)
        await db.commit()

        return await GoalService.get_goal(db, user_id, goal_id)

    @staticmethod
    async def delete_goal(
        db: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID
    ) -> dict[str, str]:
        """Deletes a goal and cascades to its contributions."""
        goal = await _get_owned_goal(db, user_id, goal_id)
        await db.delete(goal)
        await db.commit()
        return {"message": "Goal successfully deleted."}

    @staticmethod
    async def add_money(
        db: AsyncSession,
        user_id: uuid.UUID,
        goal_id: uuid.UUID,
        contrib_in: GoalContributionCreate,
    ) -> GoalResponse:
        """Adds funds to a goal and records the contribution."""
        if contrib_in.amount <= ZERO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contribution amount must be greater than zero.",
            )

        await _ensure_account_owned(db, user_id, contrib_in.account_id)

        # Row lock so concurrent deposits cannot overwrite each other's balance update
        goal = await _get_owned_goal(db, user_id, goal_id, for_update=True)

        db.add(
            GoalContribution(
                goal_id=goal.id,
                user_id=user_id,
                account_id=contrib_in.account_id,
                amount=contrib_in.amount,
                date=contrib_in.date or date.today(),
                notes=contrib_in.notes,
            )
        )
        goal.current_amount = goal.current_amount + contrib_in.amount
        _sync_completion_status(goal)
        goal.updated_at = datetime.now(UTC)

        await db.commit()
        return await GoalService.get_goal(db, user_id, goal.id)

    @staticmethod
    async def remove_contribution(
        db: AsyncSession,
        user_id: uuid.UUID,
        goal_id: uuid.UUID,
        contribution_id: uuid.UUID,
    ) -> GoalResponse:
        """Undoes a contribution, taking its amount back off the goal."""
        goal = await _get_owned_goal(db, user_id, goal_id, for_update=True)

        stmt = select(GoalContribution).where(
            GoalContribution.id == contribution_id, GoalContribution.goal_id == goal.id
        )
        contribution = (await db.execute(stmt)).scalar_one_or_none()
        if contribution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contribution not found or access denied.",
            )

        goal.current_amount = max(ZERO, goal.current_amount - contribution.amount)
        _sync_completion_status(goal)
        goal.updated_at = datetime.now(UTC)
        await db.delete(contribution)

        await db.commit()
        return await GoalService.get_goal(db, user_id, goal.id)

    @staticmethod
    async def get_goals_totals(
        db: AsyncSession, user_id: uuid.UUID, as_of_date: date | None = None
    ) -> GoalsSummaryResponse:
        """Aggregates saved, left and target amounts across all of the user's goals."""
        goals = await GoalService.list_goals(db, user_id, as_of_date=as_of_date)
        total_saved = sum((g.current_amount for g in goals), ZERO)
        total_target = sum((g.target_amount for g in goals), ZERO)
        total_left = sum((g.progress.left for g in goals), ZERO)

        return GoalsSummaryResponse(
            total_saved=total_saved,
            total_left=total_left,
            total_target=total_target,
            count=len(goals),
            goals=goals,
        )
