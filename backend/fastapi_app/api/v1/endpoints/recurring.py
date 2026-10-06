"""API Router for DHAN Recurring Payments, Bills, EMIs, and Subscriptions."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import get_current_user, get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.recurring import (
    RecurringBatchTriggerResponse,
    RecurringPaymentCreate,
    RecurringPaymentResponse,
    RecurringPaymentUpdate,
    RecurringSummaryResponse,
    RecurringTriggerRequest,
    RecurringTriggerResponse,
)
from fastapi_app.services.recurring_service import RecurringService

router = APIRouter(prefix="/recurring", tags=["Recurring Payments"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.post("", response_model=RecurringPaymentResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/",
    response_model=RecurringPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_recurring_payment(
    payment_in: RecurringPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPaymentResponse:
    """Create a new recurring bill, subscription, EMI, or scheduled income."""
    return await RecurringService.create_payment(
        db=db, user_id=current_user.id, payment_in=payment_in
    )


@router.get("", response_model=list[RecurringPaymentResponse])
@router.get("/", response_model=list[RecurringPaymentResponse], include_in_schema=False)
async def list_recurring_payments(
    kind: str | None = Query(
        None, description="Filter by kind: bill, emi, subscription, income, expense"
    ),
    frequency: str | None = Query(
        None, description="Filter by frequency: daily, weekly, monthly, quarterly, yearly"
    ),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status: active, inactive, paused"
    ),
    month: str | None = Query(
        None, pattern=MONTH_PATTERN, description="Filter by due month e.g. 2026-10"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecurringPaymentResponse]:
    """List recurring payments owned by user with flexible filtering."""
    return await RecurringService.list_payments(
        db=db,
        user_id=current_user.id,
        kind=kind,
        frequency=frequency,
        status_filter=status_filter,
        month=month,
    )


@router.get("/summary", response_model=RecurringSummaryResponse)
async def get_recurring_summary(
    month: str | None = Query(
        None, pattern=MONTH_PATTERN, description="Target month in YYYY-MM format"
    ),
    as_of: date | None = Query(
        None, description="Client's local date for the 7-day window (defaults to server date)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringSummaryResponse:
    """Get aggregated outgoing commitments, subscriptions breakdown, and upcoming 7-day bills."""
    return await RecurringService.get_summary(
        db=db, user_id=current_user.id, month=month, as_of_date=as_of
    )


@router.get("/{id}", response_model=RecurringPaymentResponse)
async def get_recurring_payment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPaymentResponse:
    """Get details of a specific recurring payment."""
    return await RecurringService.get_payment(db=db, user_id=current_user.id, payment_id=id)


@router.patch("/{id}", response_model=RecurringPaymentResponse)
async def update_recurring_payment(
    id: uuid.UUID,
    update_in: RecurringPaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPaymentResponse:
    """Update title, amount, frequency, next due date, or status."""
    return await RecurringService.update_payment(
        db=db, user_id=current_user.id, payment_id=id, update_in=update_in
    )


@router.delete("/{id}", response_model=dict[str, str])
async def delete_recurring_payment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a recurring payment definition."""
    return await RecurringService.delete_payment(db=db, user_id=current_user.id, payment_id=id)


@router.post("/{id}/deactivate", response_model=RecurringPaymentResponse)
async def deactivate_recurring_payment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPaymentResponse:
    """Deactivate a recurring payment."""
    return await RecurringService.deactivate_payment(db=db, user_id=current_user.id, payment_id=id)


@router.post("/{id}/activate", response_model=RecurringPaymentResponse)
async def activate_recurring_payment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringPaymentResponse:
    """Reactivate a paused or inactive recurring payment; missed occurrences are skipped."""
    return await RecurringService.activate_payment(db=db, user_id=current_user.id, payment_id=id)


@router.post("/{id}/trigger", response_model=RecurringTriggerResponse)
async def trigger_recurring_payment(
    id: uuid.UUID,
    trigger_in: RecurringTriggerRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringTriggerResponse:
    """Explicitly trigger execution of a recurring payment, generating a ledger transaction."""
    return await RecurringService.execute_payment(
        db=db,
        user_id=current_user.id,
        payment_id=id,
        execution_date=trigger_in.execution_date if trigger_in else None,
        dry_run=trigger_in.dry_run if trigger_in else False,
        expected_due_date=trigger_in.expected_due_date if trigger_in else None,
    )


@router.post("/process-due", response_model=RecurringBatchTriggerResponse)
async def process_due_recurring_payments(
    dry_run: bool = Query(False, description="If true, simulate without modifying database"),
    auto_pay_only: bool = Query(
        True, description="Book only auto-pay payments; false books every due active payment"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecurringBatchTriggerResponse:
    """Run the due-payments job now for the authenticated user (one occurrence per payment)."""
    return await RecurringService.process_due_payments(
        db=db,
        user_id=current_user.id,
        dry_run=dry_run,
        auto_pay_only=auto_pay_only,
    )
