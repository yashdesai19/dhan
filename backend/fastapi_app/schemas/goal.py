"""Pydantic schemas for DHAN Goals and Contributions."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class GoalContributionCreate(BaseModel):
    """Payload to add money / contribution to a goal."""

    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=15,
        decimal_places=2,
        description="Contribution amount in Rupees (must be positive)",
    )
    account_id: uuid.UUID | None = Field(
        None, description="Optional account from which contribution was transferred"
    )
    date: dt.date | None = Field(
        None, description="Contribution date; defaults to today if omitted"
    )
    notes: str | None = Field(
        None, max_length=500, description="Optional note describing the deposit"
    )


class GoalContributionResponse(BaseModel):
    """Serialised Goal contribution record."""

    id: uuid.UUID
    goal_id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID | None = None
    amount: Decimal
    date: dt.date
    notes: str | None = None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class GoalProgressResponse(BaseModel):
    """Calculated goal metrics and progress indicators conforming to product invariants."""

    saved: Decimal
    left: Decimal
    pct: int = Field(..., description="Integer percentage of target saved (0-100+)")
    months_left: int
    monthly: Decimal = Field(
        ..., description="Rupees per month needed to hit target by target_date"
    )
    status: str = Field(..., description="'onTrack' | 'behind' | 'done'")
    pill: str = Field(
        ..., description="UI pill text: e.g. 'Done', 'Behind', 'On track', or '₹12,500/mo'"
    )


class GoalCreate(BaseModel):
    """Payload to establish a new financial savings target."""

    name: str = Field(
        ..., min_length=1, max_length=150, description="Target name e.g. MacBook, Emergency Fund"
    )
    target_amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=15,
        decimal_places=2,
        description="Target amount in Rupees (must be positive)",
    )
    target_date: dt.date = Field(..., description="Target completion deadline date")
    icon: str = Field(
        "target", max_length=50, description="Icon identifier e.g. laptop, shield, plane"
    )
    initial_amount: Decimal = Field(
        Decimal("0.00"),
        ge=0,
        max_digits=15,
        decimal_places=2,
        description="Initial money deposited",
    )
    account_id: uuid.UUID | None = Field(None, description="Source account for initial deposit")
    created_at: dt.datetime | None = Field(
        None, description="Optional creation timestamp for historical goals"
    )


class GoalUpdate(BaseModel):
    """Payload to update an existing goal."""

    name: str | None = Field(None, min_length=1, max_length=150)
    target_amount: Decimal | None = Field(None, gt=0, max_digits=15, decimal_places=2)
    target_date: dt.date | None = None
    icon: str | None = Field(None, max_length=50)
    status: str | None = Field(
        None,
        pattern="^(in_progress|achieved|paused|cancelled)$",
        description="in_progress/achieved follow the saved amount; achieved needs the target met",
    )
    created_at: dt.datetime | None = None


class GoalResponse(BaseModel):
    """Serialised Goal representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    icon: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: dt.date
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime
    progress: GoalProgressResponse
    contributions: list[GoalContributionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class GoalsSummaryResponse(BaseModel):
    """Aggregated financial savings across all user goals."""

    total_saved: Decimal
    total_left: Decimal
    total_target: Decimal
    count: int
    goals: list[GoalResponse]
