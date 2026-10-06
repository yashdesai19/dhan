"""Pydantic schemas for DHAN reports: monthly totals, category spending and daily spending."""

import datetime as dt
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class ReportPeriod(BaseModel):
    """The calendar month a report covers, on the user's wall clock."""

    month: str = Field(..., description="YYYY-MM")
    timezone: str = Field(..., description="IANA zone used for day and month boundaries")
    period_start: dt.datetime = Field(..., description="First instant of the month (inclusive)")
    period_end: dt.datetime = Field(..., description="First instant after the month (exclusive)")


class MonthPoint(BaseModel):
    """Income and spending for one month of the trend."""

    month: str
    income: Decimal
    spent: Decimal
    net: Decimal


class MonthlyReportResponse(ReportPeriod):
    """Spec §6 monthly figures. Transfers between the user's own accounts are neither income
    nor spending; they are reported separately."""

    income: Decimal
    spent: Decimal
    net: Decimal = Field(..., description="Net flow: income - spent")
    savings_rate: int = Field(
        ..., description="Whole-number % of income kept (net / income); 0 when there's no income"
    )
    transfers: Decimal = Field(..., description="Moved between the user's own accounts")
    income_count: int
    expense_count: int
    trend: list[MonthPoint] = Field(..., description="Oldest first, ending with this month")


class CategorySpend(BaseModel):
    """One category's share of the month."""

    category_id: uuid.UUID | None = Field(
        default=None, description="None for uncategorised transactions"
    )
    name: str
    icon: str | None = None
    color: str | None = None
    amount: Decimal
    count: int
    share: Decimal = Field(..., description="% of the month's total, one decimal place")


class CategoryReportResponse(ReportPeriod):
    """Spending (or income) per category, largest first."""

    type: str = Field(..., description="expense or income")
    total: Decimal
    count: int
    categories: list[CategorySpend]


class DaySpend(BaseModel):
    """One local calendar day."""

    date: dt.date
    spent: Decimal
    income: Decimal
    count: int = Field(..., description="Income and expense transactions that day")


class DailyReportResponse(ReportPeriod):
    """Every day of the month, including days with nothing recorded."""

    days_in_month: int
    total_spent: Decimal
    total_income: Decimal
    days_counted: int = Field(
        ..., description="Days elapsed so far (all of them for a past month, 0 for a future one)"
    )
    average_daily_spent: Decimal = Field(..., description="total_spent / days_counted")
    highest_day: DaySpend | None = Field(
        default=None, description="Day with the most spending, if any"
    )
    days: list[DaySpend]
