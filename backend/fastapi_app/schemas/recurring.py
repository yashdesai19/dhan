"""Pydantic schemas for DHAN Recurring Payments, Bills, EMIs, and Subscriptions."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RecurringPaymentCreate(BaseModel):
    """Payload to register a new recurring bill, subscription, EMI, or scheduled income."""

    title: str = Field(
        ..., min_length=1, max_length=150, description="Title/name e.g. Netflix, Rent, Salary"
    )
    kind: str = Field(
        "bill",
        pattern="^(bill|emi|subscription|income|expense)$",
        description="Payment kind: bill, emi, subscription, income, or expense",
    )
    amount: Decimal = Field(
        ..., gt=0, max_digits=15, decimal_places=2, description="Recurring amount in Rupees"
    )
    account_id: uuid.UUID = Field(..., description="Linked Account ID")
    category_id: uuid.UUID | None = Field(None, description="Optional linked Category ID")
    frequency: str = Field(
        "monthly",
        pattern="^(daily|weekly|monthly|quarterly|yearly)$",
        description="Frequency cadence: daily, weekly, monthly, quarterly, yearly",
    )
    next_due_date: date = Field(..., description="Next execution / due date")
    status: str = Field(
        "active",
        pattern="^(active|inactive|paused|cancelled)$",
        description="Current state: active, inactive, paused, or cancelled",
    )
    auto_pay: bool = Field(False, description="Whether automatic execution is enabled")
    notes: str | None = Field(
        None, max_length=500, description="Optional payment notes or description"
    )
    metadata_json: dict[str, Any] | None = Field(
        None,
        description="Optional metadata e.g. emi {paid, total, remaining}, letter, icon",
    )


class RecurringPaymentUpdate(BaseModel):
    """Payload to update an existing recurring payment."""

    title: str | None = Field(None, min_length=1, max_length=150)
    kind: str | None = Field(None, pattern="^(bill|emi|subscription|income|expense)$")
    amount: Decimal | None = Field(None, gt=0, max_digits=15, decimal_places=2)
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    frequency: str | None = Field(None, pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    next_due_date: date | None = None
    status: str | None = Field(None, pattern="^(active|inactive|paused|cancelled)$")
    auto_pay: bool | None = None
    notes: str | None = Field(None, max_length=500)
    metadata_json: dict[str, Any] | None = None

    # category_id, notes and metadata_json can be cleared by sending null; omitted fields and
    # nulls for the required fields leave the stored value unchanged.


class RecurringPaymentResponse(BaseModel):
    """Serialised Recurring Payment representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    title: str
    kind: str
    amount: Decimal
    frequency: str
    next_due_date: date
    anchor_day: int | None = None
    status: str
    auto_pay: bool
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None
    last_paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        """Convenience boolean indicator matching active status."""
        return self.status == "active"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> str:
        """Alias matching domain naming."""
        return self.title

    model_config = ConfigDict(from_attributes=True)


class RecurringTriggerRequest(BaseModel):
    """Parameters for explicitly triggering recurring payment execution."""

    execution_date: date | None = Field(
        None, description="Explicit date for transaction creation (defaults to next_due_date)"
    )
    dry_run: bool = Field(
        False, description="If true, computes resulting transaction without applying state changes"
    )
    expected_due_date: date | None = Field(
        None,
        description=(
            "Occurrence the caller means to book; 409 if the payment has already moved past it. "
            "Makes retries and double-taps safe."
        ),
    )


class RecurringTriggerResponse(BaseModel):
    """Outcome of recurring payment execution."""

    recurring_payment_id: uuid.UUID
    transaction_id: uuid.UUID | None
    title: str
    amount: Decimal
    execution_date: date
    previous_due_date: date
    new_due_date: date
    dry_run: bool
    status: str


class RecurringBatchTriggerResponse(BaseModel):
    """Summary of batch recurring execution."""

    as_of: date
    processed_count: int
    executed_count: int = Field(..., description="Occurrences booked (or simulated in a dry run)")
    skipped_count: int = Field(..., description="Already booked by an overlapping run")
    failed_count: int
    dry_run: bool
    results: list[RecurringTriggerResponse]


class RecurringSummaryResponse(BaseModel):
    """Monthly breakdown and subscription analysis for recurring commitments."""

    month: str
    outgoing_total: Decimal
    outgoing_count: int
    incoming_total: Decimal
    incoming_count: int
    subscriptions_monthly: Decimal
    subscriptions_yearly: Decimal
    subscriptions_count: int
    upcoming_soon_total: Decimal
    upcoming_soon: list[RecurringPaymentResponse]
    upcoming_later: list[RecurringPaymentResponse]
