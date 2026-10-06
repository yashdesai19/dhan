"""API Router for DHAN reports. Every figure is computed from the authenticated user's own data."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import get_current_user, get_db
from fastapi_app.core.periods import MONTH_PATTERN, get_timezone, parse_month, today_in
from fastapi_app.models.user import User
from fastapi_app.schemas.report import (
    CategoryReportResponse,
    DailyReportResponse,
    MonthlyReportResponse,
)
from fastapi_app.services.report_service import Period, ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


def report_period(
    month: str | None = Query(
        None, pattern=MONTH_PATTERN, description="YYYY-MM; defaults to the current month in tz"
    ),
    tz: str | None = Query(
        None,
        description="IANA time zone for day and month boundaries (default Asia/Kolkata)",
    ),
) -> Period:
    """The month being reported on, in the user's time zone."""
    try:
        zone = get_timezone(tz)
        if month is None:
            today = today_in(zone)
            return Period(today.year, today.month, zone)
        return Period(*parse_month(month), zone)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None


@router.get("/monthly", response_model=MonthlyReportResponse)
async def monthly_report(
    period: Period = Depends(report_period),
    months: int = Query(6, ge=1, le=24, description="Months of trend, ending with this month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyReportResponse:
    """Income, spending, net flow and savings rate for a month, plus a trend."""
    return await ReportService.monthly(db, current_user.id, period, trend_months=months)


@router.get("/categories", response_model=CategoryReportResponse)
async def category_report(
    period: Period = Depends(report_period),
    txn_type: str = Query(
        "expense", alias="type", pattern="^(expense|income)$", description="expense or income"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryReportResponse:
    """Spending (or income) per category for a month, largest first."""
    return await ReportService.categories(db, current_user.id, period, txn_type=txn_type)


@router.get("/daily", response_model=DailyReportResponse)
async def daily_report(
    period: Period = Depends(report_period),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyReportResponse:
    """Spending and income for each day of a month."""
    return await ReportService.daily(db, current_user.id, period)
