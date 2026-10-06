"""Service layer for DHAN reports (mirrors utils/summary.ts and utils/reports.ts in the app).

Every query filters on the requesting user's id, so a report can only ever see that user's
transactions. Only completed transactions count; pending, failed and cancelled ones don't.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.periods import (
    days_in_month,
    local_date,
    month_bounds,
    month_key,
    shift_month,
    today_in,
)
from fastapi_app.models.category import Category
from fastapi_app.models.transaction import Transaction
from fastapi_app.schemas.report import (
    CategoryReportResponse,
    CategorySpend,
    DailyReportResponse,
    DaySpend,
    MonthlyReportResponse,
    MonthPoint,
)

ZERO = Decimal("0.00")
COUNTED_STATUS = "completed"


def js_round(value: Decimal) -> int:
    """Nearest whole number with halves going towards +infinity, exactly like JS Math.round."""
    return int((value + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR))


def savings_rate(net: Decimal, income: Decimal) -> int:
    """Whole-number % of income kept, as utils/format.ts percent(net, income); 0 without income."""
    if income == 0:
        return 0
    return js_round(net / income * 100)


@dataclass(frozen=True)
class Period:
    """A calendar month in a time zone."""

    year: int
    month: int
    tz: ZoneInfo

    @property
    def key(self) -> str:
        return month_key(self.year, self.month)

    @property
    def bounds(self) -> tuple[datetime, datetime]:
        return month_bounds(self.year, self.month, self.tz)

    def shifted(self, delta: int) -> "Period":
        return Period(*shift_month(self.year, self.month, delta), self.tz)

    def header(self) -> dict[str, Any]:
        start, end = self.bounds
        return {
            "month": self.key,
            "timezone": self.tz.key,
            "period_start": start,
            "period_end": end,
        }


def _counted_in(user_id: uuid.UUID, period: Period) -> tuple[ColumnElement[bool], ...]:
    """The user's completed transactions dated within the period (half-open range)."""
    start, end = period.bounds
    return (
        Transaction.user_id == user_id,
        Transaction.status == COUNTED_STATUS,
        Transaction.transaction_date >= start,
        Transaction.transaction_date < end,
    )


async def _totals_by_type(
    db: AsyncSession, user_id: uuid.UUID, period: Period
) -> dict[str, tuple[Decimal, int]]:
    """{'income': (sum, count), 'expense': ..., 'transfer': ...} for the period."""
    stmt = (
        select(Transaction.type, func.sum(Transaction.amount), func.count())
        .where(*_counted_in(user_id, period))
        .group_by(Transaction.type)
    )
    return {kind: (Decimal(total), count) for kind, total, count in (await db.execute(stmt)).all()}


class ReportService:
    """Monthly totals, category breakdowns and daily spending for one user."""

    @staticmethod
    async def monthly(
        db: AsyncSession, user_id: uuid.UUID, period: Period, trend_months: int = 6
    ) -> MonthlyReportResponse:
        """Income, spending, net flow and savings rate. Spending is expense transactions only:
        transfers move money between the user's own accounts (spec §6)."""
        totals = await _totals_by_type(db, user_id, period)
        income, income_count = totals.get("income", (ZERO, 0))
        spent, expense_count = totals.get("expense", (ZERO, 0))
        transfers, _ = totals.get("transfer", (ZERO, 0))
        net = income - spent

        trend: list[MonthPoint] = []
        for delta in range(1 - trend_months, 1):
            month = period.shifted(delta)
            month_totals = totals if delta == 0 else await _totals_by_type(db, user_id, month)
            m_income = month_totals.get("income", (ZERO, 0))[0]
            m_spent = month_totals.get("expense", (ZERO, 0))[0]
            trend.append(
                MonthPoint(month=month.key, income=m_income, spent=m_spent, net=m_income - m_spent)
            )

        return MonthlyReportResponse(
            **period.header(),
            income=income,
            spent=spent,
            net=net,
            savings_rate=savings_rate(net, income),
            transfers=transfers,
            income_count=income_count,
            expense_count=expense_count,
            trend=trend,
        )

    @staticmethod
    async def categories(
        db: AsyncSession, user_id: uuid.UUID, period: Period, txn_type: str = "expense"
    ) -> CategoryReportResponse:
        """Per-category totals, largest first. Uncategorised transactions get their own row, so
        the rows always add up to the month's total."""
        stmt = (
            select(
                Transaction.category_id,
                Category.name,
                Category.icon,
                Category.color,
                func.sum(Transaction.amount),
                func.count(),
            )
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(*_counted_in(user_id, period), Transaction.type == txn_type)
            .group_by(Transaction.category_id, Category.name, Category.icon, Category.color)
        )
        rows = (await db.execute(stmt)).all()
        total = sum((Decimal(amount) for *_, amount, _count in rows), ZERO)

        def share(amount: Decimal) -> Decimal:
            if total == 0:
                return Decimal("0.0")
            return (amount / total * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        categories = [
            CategorySpend(
                category_id=category_id,
                name=name or "Uncategorised",
                icon=icon or None,
                color=color or None,
                amount=Decimal(amount),
                count=count,
                share=share(Decimal(amount)),
            )
            for category_id, name, icon, color, amount, count in rows
        ]
        categories.sort(key=lambda c: (-c.amount, c.name))

        return CategoryReportResponse(
            **period.header(),
            type=txn_type,
            total=total,
            count=sum(c.count for c in categories),
            categories=categories,
        )

    @staticmethod
    async def daily(db: AsyncSession, user_id: uuid.UUID, period: Period) -> DailyReportResponse:
        """Spending and income for every local day of the month."""
        stmt = select(Transaction.type, Transaction.amount, Transaction.transaction_date).where(
            *_counted_in(user_id, period), Transaction.type.in_(("expense", "income"))
        )
        spent: dict[date, Decimal] = defaultdict(lambda: ZERO)
        income: dict[date, Decimal] = defaultdict(lambda: ZERO)
        counts: dict[date, int] = defaultdict(int)
        for kind, amount, when in (await db.execute(stmt)).all():
            day = local_date(when, period.tz)
            (spent if kind == "expense" else income)[day] += amount
            counts[day] += 1

        total_days = days_in_month(period.year, period.month)
        days = [
            DaySpend(date=day, spent=spent[day], income=income[day], count=counts[day])
            for day in (date(period.year, period.month, d) for d in range(1, total_days + 1))
        ]
        total_spent = sum((d.spent for d in days), ZERO)

        today = today_in(period.tz)
        if (period.year, period.month) < (today.year, today.month):
            days_counted = total_days
        elif (period.year, period.month) == (today.year, today.month):
            days_counted = today.day
        else:
            days_counted = 0
        average = (
            (total_spent / days_counted).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if days_counted
            else ZERO
        )
        # max() keeps the first of equal days, i.e. the earliest
        highest = max(days, key=lambda d: d.spent) if total_spent > 0 else None

        return DailyReportResponse(
            **period.header(),
            days_in_month=total_days,
            total_spent=total_spent,
            total_income=sum((d.income for d in days), ZERO),
            days_counted=days_counted,
            average_daily_spent=average,
            highest_day=highest,
            days=days,
        )
