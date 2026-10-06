"""Pydantic schemas for DHAN Budgets."""

import calendar
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fastapi_app.schemas.category import CategoryResponse


def compute_month_range(year: int, month: int) -> tuple[date, date]:
    """Calculate the first and last dates of a given year and month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


class BudgetBase(BaseModel):
    """Base schema for budget limits and periods."""

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        max_digits=15,
        description="Budget ceiling amount (must be positive)",
    )
    category_id: uuid.UUID | None = Field(
        default=None,
        description="Associated category ID (None indicates an overall monthly budget)",
    )
    month: str | None = Field(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Target month in YYYY-MM format",
    )
    period: str = Field(
        default="monthly",
        description="Budget periodicity: monthly, weekly, yearly",
    )
    start_date: date | None = None
    end_date: date | None = None
    warn_at_percent: int = Field(
        default=90,
        ge=1,
        le=100,
        description="Warning threshold percentage (1 to 100)",
    )
    rollover: bool = Field(
        default=False,
        description="Whether unused budget balance rolls over to the next period",
    )


class BudgetCreate(BudgetBase):
    """Schema for creating a new monthly or category budget."""

    @model_validator(mode="before")
    @classmethod
    def populate_dates_and_month(cls, data: Any) -> Any:
        if isinstance(data, dict):
            month_val = data.get("month")
            s_date = data.get("start_date")
            e_date = data.get("end_date")

            if month_val and not (s_date and e_date):
                try:
                    parts = month_val.split("-")
                    year, month = int(parts[0]), int(parts[1])
                    start, end = compute_month_range(year, month)
                    data["start_date"] = start
                    data["end_date"] = end
                except Exception:
                    pass
            elif s_date and e_date:
                if isinstance(s_date, str):
                    s_date = date.fromisoformat(s_date)
                if not month_val and hasattr(s_date, "strftime"):
                    data["month"] = s_date.strftime("%Y-%m")
            elif not month_val and not s_date and not e_date:
                today = date.today()
                start, end = compute_month_range(today.year, today.month)
                data["start_date"] = start
                data["end_date"] = end
                data["month"] = today.strftime("%Y-%m")
        return data

    @model_validator(mode="after")
    def validate_date_order(self) -> "BudgetCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class CategoryBudgetCreate(BaseModel):
    """Convenience schema to set a budget ceiling for a specific category."""

    category_id: uuid.UUID = Field(..., description="Target category ID")
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=15)
    month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    warn_at_percent: int = Field(default=90, ge=1, le=100)
    rollover: bool = Field(default=False)


class BudgetUpdate(BaseModel):
    """Schema for modifying existing budget limits or parameters."""

    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=15)
    category_id: uuid.UUID | None = None
    month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    period: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    warn_at_percent: int | None = Field(default=None, ge=1, le=100)
    rollover: bool | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "BudgetUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class BudgetResponse(BaseModel):
    """Detailed response schema for a single budget, including derived spending metrics."""

    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category: CategoryResponse | None = None
    amount: Decimal
    spent: Decimal
    remaining: Decimal
    percentage_used: float
    tone: str  # 'ok', 'warn', 'over'
    period: str
    month: str | None = None
    start_date: date
    end_date: date
    warn_at_percent: int
    rollover: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryBudgetStatus(BaseModel):
    """Status breakdown for an individual category's budget within a given month."""

    category_id: uuid.UUID
    category_name: str
    category_icon: str | None = None
    limit: Decimal
    spent: Decimal
    remaining: Decimal
    percentage_used: float
    tone: str
    warn_at_percent: int


class BudgetSummaryResponse(BaseModel):
    """Aggregated monthly budget status matching the DHAN domain specification."""

    month: str
    limit: Decimal
    spent: Decimal
    remaining: Decimal
    percentage_used: float
    tone: str
    categories: list[CategoryBudgetStatus]
