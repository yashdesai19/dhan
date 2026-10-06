"""Business logic, dynamic financial calculations, and service layer for DHAN Budgets."""

import calendar
import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi_app.core.periods import days_bounds, get_timezone
from fastapi_app.models.budget import Budget
from fastapi_app.models.category import Category
from fastapi_app.models.transaction import Transaction
from fastapi_app.schemas.budget import (
    BudgetCreate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetUpdate,
    CategoryBudgetStatus,
)


def compute_month_range(year: int, month: int) -> tuple[date, date]:
    """Calculate the first and last dates of a given year and month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def tone_for(pct: float, warn_at: int) -> str:
    """Determine visual budget health tone based on usage percentage."""
    if pct > 100.0:
        return "over"
    if pct >= float(warn_at):
        return "warn"
    return "ok"


async def _validate_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None,
) -> Category | None:
    """Verify category exists and belongs to the user or is a system default."""
    if category_id is None:
        return None
    query = select(Category).where(
        Category.id == category_id,
        (Category.user_id == user_id) | (Category.is_default.is_(True)),
    )
    result = await db.execute(query)
    cat = result.scalars().first()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category_id}' not found or does not belong to user.",
        )
    return cat


async def calculate_budget_spent(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
    category_id: uuid.UUID | None = None,
) -> Decimal:
    """Dynamically aggregate total expense transactions for a user within a date range and optional category.

    Income and transfer transactions are strictly excluded from spending totals.
    start_date..end_date are whole local days (end inclusive) in the default time zone, the same
    boundaries the reports use, so the last day of the month counts in full.
    """
    start, end = days_bounds(start_date, end_date, get_timezone())
    stmt = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "expense",
        Transaction.status == "completed",
        Transaction.transaction_date >= start,
        Transaction.transaction_date < end,
    )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)

    result = await db.execute(stmt)
    spent = result.scalar_one()
    return Decimal(str(spent))


async def build_budget_response(db: AsyncSession, budget: Budget) -> BudgetResponse:
    """Construct a full BudgetResponse with on-the-fly calculated spent, remaining, and percentage."""
    spent = await calculate_budget_spent(
        db=db,
        user_id=budget.user_id,
        start_date=budget.start_date,
        end_date=budget.end_date,
        category_id=budget.category_id,
    )
    remaining = budget.amount - spent
    pct = round(float((spent / budget.amount) * 100), 2) if budget.amount > Decimal("0.00") else 0.0
    tone = tone_for(pct, budget.warn_at_percent)

    category_name = budget.category.name if budget.category else None
    category_icon = budget.category.icon if budget.category else None

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        category_name=category_name,
        category_icon=category_icon,
        category=budget.category,  # type: ignore[arg-type]
        amount=budget.amount,
        spent=spent,
        remaining=remaining,
        percentage_used=pct,
        tone=tone,
        period=budget.period,
        month=budget.month,
        start_date=budget.start_date,
        end_date=budget.end_date,
        warn_at_percent=budget.warn_at_percent,
        rollover=budget.rollover,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


async def create_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: BudgetCreate,
) -> BudgetResponse:
    """Create a new monthly or category-specific budget ceiling."""
    # 1. Validate category if provided
    await _validate_category(db, user_id, data.category_id)

    # 2. Determine month and date boundaries
    start_date = data.start_date
    end_date = data.end_date
    month_str = data.month

    if not start_date or not end_date:
        if month_str:
            parts = month_str.split("-")
            year, m = int(parts[0]), int(parts[1])
            start_date, end_date = compute_month_range(year, m)
        else:
            today = date.today()
            start_date, end_date = compute_month_range(today.year, today.month)
            month_str = today.strftime("%Y-%m")

    if not month_str and start_date:
        month_str = start_date.strftime("%Y-%m")

    # 3. Check for duplicates in the same month/period
    dup_stmt = select(Budget).where(
        Budget.user_id == user_id,
        Budget.month == month_str,
    )
    if data.category_id is not None:
        dup_stmt = dup_stmt.where(Budget.category_id == data.category_id)
    else:
        dup_stmt = dup_stmt.where(Budget.category_id.is_(None))

    dup_result = await db.execute(dup_stmt)
    if dup_result.scalars().first() is not None:
        scope = "for this category" if data.category_id else "overall"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A budget {scope} already exists for month {month_str}.",
        )

    # 4. Insert new budget
    new_budget = Budget(
        user_id=user_id,
        category_id=data.category_id,
        amount=data.amount,
        period=data.period,
        month=month_str,
        start_date=start_date,
        end_date=end_date,
        warn_at_percent=data.warn_at_percent,
        rollover=data.rollover,
    )
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget, attribute_names=["category"])

    return await build_budget_response(db, new_budget)


async def get_budget_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> BudgetResponse:
    """Retrieve an existing budget by ID, enforcing user ownership."""
    stmt = (
        select(Budget)
        .options(selectinload(Budget.category))
        .where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    result = await db.execute(stmt)
    budget = result.scalars().first()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_id}' not found or does not belong to user.",
        )
    return await build_budget_response(db, budget)


async def list_budgets(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: str | None = None,
    category_id: uuid.UUID | None = None,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[BudgetResponse]:
    """List budgets for the authenticated user with optional filtering."""
    stmt = select(Budget).options(selectinload(Budget.category)).where(Budget.user_id == user_id)

    if month:
        stmt = stmt.where(Budget.month == month)
    if category_id:
        stmt = stmt.where(Budget.category_id == category_id)
    if period:
        stmt = stmt.where(Budget.period == period)
    if start_date:
        stmt = stmt.where(Budget.start_date >= start_date)
    if end_date:
        stmt = stmt.where(Budget.end_date <= end_date)

    stmt = stmt.order_by(Budget.start_date.desc(), Budget.created_at.desc())
    result = await db.execute(stmt)
    budgets = result.scalars().all()

    return [await build_budget_response(db, b) for b in budgets]


async def update_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
    data: BudgetUpdate,
) -> BudgetResponse:
    """Update an existing budget with validation and immediate recalculation."""
    stmt = (
        select(Budget)
        .options(selectinload(Budget.category))
        .where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    result = await db.execute(stmt)
    budget = result.scalars().first()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_id}' not found or does not belong to user.",
        )

    if data.amount is not None:
        budget.amount = data.amount

    if data.category_id is not None:
        await _validate_category(db, user_id, data.category_id)
        budget.category_id = data.category_id

    if data.month is not None:
        budget.month = data.month
        if not data.start_date or not data.end_date:
            parts = data.month.split("-")
            year, m = int(parts[0]), int(parts[1])
            s, e = compute_month_range(year, m)
            budget.start_date = s
            budget.end_date = e

    if data.start_date is not None:
        budget.start_date = data.start_date
    if data.end_date is not None:
        budget.end_date = data.end_date
    if data.period is not None:
        budget.period = data.period
    if data.warn_at_percent is not None:
        budget.warn_at_percent = data.warn_at_percent
    if data.rollover is not None:
        budget.rollover = data.rollover

    budget.updated_at = datetime.now(budget.created_at.tzinfo)

    await db.commit()
    await db.refresh(budget, attribute_names=["category"])
    return await build_budget_response(db, budget)


async def delete_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> None:
    """Delete a budget, ensuring user ownership."""
    stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    result = await db.execute(stmt)
    budget = result.scalars().first()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget '{budget_id}' not found or does not belong to user.",
        )
    await db.delete(budget)
    await db.commit()


async def get_budget_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: str | None = None,
) -> BudgetSummaryResponse:
    """Retrieve full monthly budget summary and category-level breakdown."""
    if not month:
        month = date.today().strftime("%Y-%m")

    parts = month.split("-")
    year, m_num = int(parts[0]), int(parts[1])
    start_date, end_date = compute_month_range(year, m_num)

    # 1. Fetch all budgets for this month
    stmt = (
        select(Budget)
        .options(selectinload(Budget.category))
        .where(
            Budget.user_id == user_id,
            Budget.month == month,
        )
        .order_by(Budget.created_at.asc())
    )
    result = await db.execute(stmt)
    budgets = result.scalars().all()

    category_statuses: list[CategoryBudgetStatus] = []
    category_budgets = [b for b in budgets if b.category_id is not None]
    overall_budget = next((b for b in budgets if b.category_id is None), None)

    total_limit = Decimal("0.00")
    total_spent = Decimal("0.00")

    if category_budgets:
        for cb in category_budgets:
            c_spent = await calculate_budget_spent(
                db=db,
                user_id=user_id,
                start_date=cb.start_date,
                end_date=cb.end_date,
                category_id=cb.category_id,
            )
            c_remaining = cb.amount - c_spent
            c_pct = (
                round(float((c_spent / cb.amount) * 100), 2) if cb.amount > Decimal("0.00") else 0.0
            )
            c_tone = tone_for(c_pct, cb.warn_at_percent)

            assert cb.category_id is not None
            category_statuses.append(
                CategoryBudgetStatus(
                    category_id=cb.category_id,
                    category_name=cb.category.name if cb.category else "Unknown",
                    category_icon=cb.category.icon if cb.category else None,
                    limit=cb.amount,
                    spent=c_spent,
                    remaining=c_remaining,
                    percentage_used=c_pct,
                    tone=c_tone,
                    warn_at_percent=cb.warn_at_percent,
                )
            )
            total_limit += cb.amount
            total_spent += c_spent
    elif overall_budget:
        total_limit = overall_budget.amount
        total_spent = await calculate_budget_spent(
            db=db,
            user_id=user_id,
            start_date=overall_budget.start_date,
            end_date=overall_budget.end_date,
            category_id=None,
        )

    remaining = total_limit - total_spent
    pct = (
        round(float((total_spent / total_limit) * 100), 2) if total_limit > Decimal("0.00") else 0.0
    )
    tone = tone_for(pct, 90)

    return BudgetSummaryResponse(
        month=month,
        limit=total_limit,
        spent=total_spent,
        remaining=remaining,
        percentage_used=pct,
        tone=tone,
        categories=category_statuses,
    )
