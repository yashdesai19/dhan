"""Service layer for DHAN Recurring Payments, Bills, EMIs, and Subscriptions."""

import calendar
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.models.account import Account
from fastapi_app.models.category import Category
from fastapi_app.models.recurring import RecurringPayment
from fastapi_app.models.transaction import Transaction
from fastapi_app.schemas.recurring import (
    RecurringBatchTriggerResponse,
    RecurringPaymentCreate,
    RecurringPaymentResponse,
    RecurringPaymentUpdate,
    RecurringSummaryResponse,
    RecurringTriggerResponse,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

MONTH_STEPS = {"monthly": 1, "quarterly": 3, "yearly": 12}
OCCURRENCES_PER_YEAR = {"daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}


def _add_months(start: date, months: int, anchor_day: int) -> date:
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))


def calculate_next_occurrence(
    current_date: date, frequency: str, anchor_day: int | None = None
) -> date:
    """Calculates the subsequent due date based on frequency cadence.

    Month-based cadences land on anchor_day (the schedule's day of month), clipped to the
    month's length, so a bill due on the 31st runs Jan 31 -> Feb 28 -> Mar 31 rather than
    drifting to the 28th. Without an anchor, current_date's day is used.
    """
    freq = frequency.lower()
    if freq == "daily":
        return current_date + timedelta(days=1)
    if freq == "weekly":
        return current_date + timedelta(weeks=1)
    if freq in MONTH_STEPS:
        return _add_months(current_date, MONTH_STEPS[freq], anchor_day or current_date.day)
    raise ValueError(f"Unsupported recurring frequency: {frequency!r}")


def effective_anchor_day(due_date: date, anchor_day: int | None) -> int:
    """The stored anchor if it is consistent with due_date, else due_date's own day.

    Guards against a due date edited outside the API (e.g. Django admin) leaving a stale anchor.
    """
    if anchor_day and due_date.day == min(
        anchor_day, calendar.monthrange(due_date.year, due_date.month)[1]
    ):
        return anchor_day
    return due_date.day


def _month_bounds(month: str) -> tuple[date, date]:
    """'2026-10' -> (2026-10-01, 2026-11-01)."""
    year, mon = (int(part) for part in month.split("-"))
    start = date(year, mon, 1)
    return start, _add_months(start, 1, 1)


async def _get_owned_payment(
    db: AsyncSession, user_id: uuid.UUID, payment_id: uuid.UUID, *, for_update: bool = False
) -> RecurringPayment:
    """Loads a recurring payment owned by the user (row-locked when for_update), else 404."""
    stmt = select(RecurringPayment).where(
        RecurringPayment.id == payment_id,
        RecurringPayment.user_id == user_id,
    )
    if for_update:
        # populate_existing: re-read the locked row even if this session already holds a copy
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    payment = (await db.execute(stmt)).scalar_one_or_none()
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring payment not found or access denied.",
        )
    return payment


async def _ensure_account_owned(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> None:
    stmt = select(Account.id).where(Account.id == account_id, Account.user_id == user_id)
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied.",
        )


async def _ensure_category_visible(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID
) -> None:
    stmt = select(Category.id).where(
        Category.id == category_id,
        (Category.user_id == user_id) | (Category.is_default.is_(True)),
    )
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or access denied.",
        )


def _skip_missed_occurrences(payment: RecurringPayment, today: date) -> None:
    """Moves next_due_date to the first occurrence on or after today.

    Used when a payment is switched back on, so occurrences that fell due while it was off are
    never back-filled by the auto-pay job.
    """
    anchor = effective_anchor_day(payment.next_due_date, payment.anchor_day)
    due = payment.next_due_date
    while due < today:
        due = calculate_next_occurrence(due, payment.frequency, anchor)
    payment.next_due_date = due


def _advance_emi(payment: RecurringPayment) -> None:
    """Counts one more EMI instalment as paid; the EMI goes inactive after the last one."""
    meta = payment.metadata_json or {}
    emi = meta.get("emi")
    if not isinstance(emi, dict):
        return
    paid = int(emi.get("paid", 0)) + 1
    total = int(emi.get("total", paid))
    if "remaining" in emi:
        remaining = Decimal(str(emi["remaining"])) - payment.amount
    else:
        remaining = payment.amount * (total - paid)
    # Stored as a string, like every money value the API returns, so it stays an exact Decimal
    emi = {**emi, "paid": paid, "remaining": str(max(ZERO, remaining).quantize(CENT))}
    payment.metadata_json = {**meta, "emi": emi}
    if paid >= total:
        payment.status = "inactive"


class RecurringService:
    """Handles lifecycle, analytics, and execution architecture for recurring commitments.

    Creating, editing or listing a recurring payment never books anything. Ledger transactions
    are created only by execute_payment, which runs when explicitly triggered (the trigger
    endpoint) or by the opt-in auto-pay job (process_due_payments).
    """

    @staticmethod
    async def create_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_in: RecurringPaymentCreate,
    ) -> RecurringPaymentResponse:
        """Registers a recurring commitment with strict account ownership checks."""
        if payment_in.amount <= ZERO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero.",
            )

        await _ensure_account_owned(db, user_id, payment_in.account_id)
        if payment_in.category_id:
            await _ensure_category_visible(db, user_id, payment_in.category_id)

        payment = RecurringPayment(
            user_id=user_id,
            account_id=payment_in.account_id,
            category_id=payment_in.category_id,
            title=payment_in.title,
            kind=payment_in.kind,
            amount=payment_in.amount,
            frequency=payment_in.frequency,
            next_due_date=payment_in.next_due_date,
            anchor_day=payment_in.next_due_date.day,
            status=payment_in.status,
            auto_pay=payment_in.auto_pay,
            notes=payment_in.notes,
            metadata_json=payment_in.metadata_json,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        return RecurringPaymentResponse.model_validate(payment)

    @staticmethod
    async def get_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
    ) -> RecurringPaymentResponse:
        """Retrieves a single recurring payment owned by user."""
        payment = await _get_owned_payment(db, user_id, payment_id)
        return RecurringPaymentResponse.model_validate(payment)

    @staticmethod
    async def list_payments(
        db: AsyncSession,
        user_id: uuid.UUID,
        kind: str | None = None,
        frequency: str | None = None,
        status_filter: str | None = None,
        month: str | None = None,
    ) -> list[RecurringPaymentResponse]:
        """Lists user recurring payments with optional filtering."""
        query = select(RecurringPayment).where(RecurringPayment.user_id == user_id)

        if kind:
            query = query.where(RecurringPayment.kind == kind)
        if frequency:
            query = query.where(RecurringPayment.frequency == frequency)
        if status_filter:
            query = query.where(RecurringPayment.status == status_filter)
        if month:
            start, end = _month_bounds(month)
            query = query.where(
                RecurringPayment.next_due_date >= start, RecurringPayment.next_due_date < end
            )

        query = query.order_by(RecurringPayment.next_due_date.asc())
        payments = (await db.execute(query)).scalars().all()
        return [RecurringPaymentResponse.model_validate(p) for p in payments]

    @staticmethod
    async def update_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
        update_in: RecurringPaymentUpdate,
    ) -> RecurringPaymentResponse:
        """Updates recurring payment properties."""
        payment = await _get_owned_payment(db, user_id, payment_id, for_update=True)
        sent = update_in.model_fields_set
        was_active = payment.status == "active"

        if update_in.account_id is not None:
            await _ensure_account_owned(db, user_id, update_in.account_id)
            payment.account_id = update_in.account_id
        if "category_id" in sent:
            if update_in.category_id is not None:
                await _ensure_category_visible(db, user_id, update_in.category_id)
            payment.category_id = update_in.category_id

        if update_in.title is not None:
            payment.title = update_in.title
        if update_in.kind is not None:
            payment.kind = update_in.kind
        if update_in.amount is not None:
            payment.amount = update_in.amount
        if update_in.frequency is not None:
            payment.frequency = update_in.frequency
        if update_in.next_due_date is not None:
            payment.next_due_date = update_in.next_due_date
            payment.anchor_day = update_in.next_due_date.day
        if update_in.status is not None:
            payment.status = update_in.status
        if update_in.auto_pay is not None:
            payment.auto_pay = update_in.auto_pay
        if "notes" in sent:
            payment.notes = update_in.notes
        if "metadata_json" in sent:
            payment.metadata_json = update_in.metadata_json

        # Re-activated without a new due date: resume from today, don't back-fill
        if not was_active and payment.status == "active" and update_in.next_due_date is None:
            _skip_missed_occurrences(payment, date.today())

        payment.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(payment)
        return RecurringPaymentResponse.model_validate(payment)

    @staticmethod
    async def delete_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
    ) -> dict[str, str]:
        """Deletes a recurring payment definition (transactions it already booked are kept)."""
        payment = await _get_owned_payment(db, user_id, payment_id)
        await db.delete(payment)
        await db.commit()
        return {"message": "Recurring payment deleted."}

    @staticmethod
    async def deactivate_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
    ) -> RecurringPaymentResponse:
        """Deactivates a recurring payment."""
        payment = await _get_owned_payment(db, user_id, payment_id, for_update=True)
        payment.status = "inactive"
        payment.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(payment)
        return RecurringPaymentResponse.model_validate(payment)

    @staticmethod
    async def activate_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> RecurringPaymentResponse:
        """Reactivates an inactive or paused recurring payment, resuming from today."""
        payment = await _get_owned_payment(db, user_id, payment_id, for_update=True)
        if payment.status != "active":
            payment.status = "active"
            _skip_missed_occurrences(payment, as_of_date or date.today())
        payment.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(payment)
        return RecurringPaymentResponse.model_validate(payment)

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        month: str | None = None,
        as_of_date: date | None = None,
    ) -> RecurringSummaryResponse:
        """Aggregates outgoing, subscriptions, and upcoming bills matching spec §6.

        Only active payments count. Month figures go by next due date, as in utils/recurring.ts.
        """
        today = as_of_date or date.today()
        target_month = month or today.strftime("%Y-%m")

        query = select(RecurringPayment).where(
            RecurringPayment.user_id == user_id,
            RecurringPayment.status == "active",
        )
        all_items = (await db.execute(query)).scalars().all()

        # Filter items for target month
        month_items = sorted(
            (p for p in all_items if p.next_due_date.strftime("%Y-%m") == target_month),
            key=lambda p: p.next_due_date,
        )

        # Outgoing (all non-income)
        outgoing_items = [p for p in month_items if p.kind != "income"]
        outgoing_total = sum((p.amount for p in outgoing_items), ZERO)

        # Incoming (salary, dividends, etc.)
        incoming_items = [p for p in month_items if p.kind == "income"]
        incoming_total = sum((p.amount for p in incoming_items), ZERO)

        # Subscriptions, normalised to their monthly cost whatever their billing cadence
        subs_items = [p for p in all_items if p.kind == "subscription"]
        subs_yearly = sum((p.amount * OCCURRENCES_PER_YEAR[p.frequency] for p in subs_items), ZERO)
        subs_monthly = (subs_yearly / 12).quantize(CENT)

        # Upcoming 7-day split
        horizon = today + timedelta(days=7)
        soon = [p for p in outgoing_items if today < p.next_due_date <= horizon]

        # Later in month: non-subscriptions OR subscriptions >= 1000
        later = [
            p
            for p in outgoing_items
            if p.next_due_date > horizon
            and (p.kind != "subscription" or p.amount >= Decimal("1000.00"))
        ]

        return RecurringSummaryResponse(
            month=target_month,
            outgoing_total=outgoing_total,
            outgoing_count=len(outgoing_items),
            incoming_total=incoming_total,
            incoming_count=len(incoming_items),
            subscriptions_monthly=subs_monthly,
            subscriptions_yearly=subs_yearly,
            subscriptions_count=len(subs_items),
            upcoming_soon_total=sum((p.amount for p in soon), ZERO),
            upcoming_soon=[RecurringPaymentResponse.model_validate(p) for p in soon],
            upcoming_later=[RecurringPaymentResponse.model_validate(p) for p in later],
        )

    # ------------------------------------------------------------------
    # Safe Recurring Execution Architecture (Explicit trigger & jobs)
    # ------------------------------------------------------------------

    @staticmethod
    async def execute_payment(
        db: AsyncSession,
        user_id: uuid.UUID,
        payment_id: uuid.UUID,
        execution_date: date | None = None,
        dry_run: bool = False,
        expected_due_date: date | None = None,
    ) -> RecurringTriggerResponse:
        """Books one occurrence: creates the ledger transaction, moves the account balance and
        advances next_due_date, all in one database transaction.

        The payment and account rows are locked for the duration. expected_due_date makes the
        call idempotent: if the payment has already moved past that occurrence (a retry, a
        double tap, an overlapping job) it raises 409 instead of booking it twice.
        Does not modify database if dry_run=True.
        """
        payment = await _get_owned_payment(db, user_id, payment_id, for_update=not dry_run)

        if payment.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute recurring payment with status '{payment.status}'.",
            )
        if expected_due_date is not None and payment.next_due_date != expected_due_date:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Occurrence {expected_due_date.isoformat()} is no longer due; "
                    f"next due date is {payment.next_due_date.isoformat()}."
                ),
            )

        prev_due = payment.next_due_date
        exec_date = execution_date or prev_due
        anchor = effective_anchor_day(prev_due, payment.anchor_day)
        next_due = calculate_next_occurrence(prev_due, payment.frequency, anchor)

        if dry_run:
            return RecurringTriggerResponse(
                recurring_payment_id=payment.id,
                transaction_id=None,
                title=payment.title,
                amount=payment.amount,
                execution_date=exec_date,
                previous_due_date=prev_due,
                new_due_date=next_due,
                dry_run=True,
                status="dry_run_success",
            )

        # 1. Lock the account for the balance update
        acc_stmt = (
            select(Account)
            .where(Account.id == payment.account_id, Account.user_id == payment.user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        account = (await db.execute(acc_stmt)).scalar_one_or_none()
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Linked account unavailable.",
            )

        # 2. Create real transaction, dated on the occurrence it pays
        tx_type = "income" if payment.kind == "income" else "expense"
        tx = Transaction(
            user_id=payment.user_id,
            account_id=payment.account_id,
            category_id=payment.category_id,
            amount=payment.amount,
            transaction_type=tx_type,
            description=payment.title,
            date=datetime.combine(exec_date, datetime.min.time(), tzinfo=UTC),
            status="completed",
            is_recurring=True,
            note=payment.notes or f"Recurring execution for {payment.title}",
        )
        db.add(tx)

        # 3. Update account balance
        balance = Decimal(str(account.balance))
        account.balance = (
            balance + payment.amount if tx_type == "income" else balance - payment.amount
        )

        # 4. Advance due date and update EMI metadata if present
        payment.next_due_date = next_due
        payment.anchor_day = anchor
        payment.last_paid_at = datetime.now(UTC)
        payment.updated_at = datetime.now(UTC)
        _advance_emi(payment)

        await db.flush()
        await db.commit()

        return RecurringTriggerResponse(
            recurring_payment_id=payment.id,
            transaction_id=tx.id,
            title=payment.title,
            amount=payment.amount,
            execution_date=exec_date,
            previous_due_date=prev_due,
            new_due_date=next_due,
            dry_run=False,
            status="executed",
        )

    @staticmethod
    async def process_due_payments(
        db: AsyncSession,
        user_id: uuid.UUID | None = None,
        as_of_date: date | None = None,
        dry_run: bool = False,
        auto_pay_only: bool = True,
    ) -> RecurringBatchTriggerResponse:
        """Batch processor for background jobs: books active payments due on or before as_of_date.

        user_id=None sweeps every user (what a scheduler would call). Safety rules:
        - auto_pay_only (default): only payments the user opted into auto-pay are booked;
          everything else waits for an explicit trigger.
        - At most one occurrence per payment per run, dated on its due date. A payment several
          periods behind catches up over successive runs instead of in one burst.
        - Each occurrence is booked with expected_due_date, so re-runs and overlapping workers
          skip what is already booked rather than double-posting.
        - Failures are isolated: the failing payment is rolled back and the batch carries on.
        """
        cutoff_date = as_of_date or date.today()
        query = (
            select(
                RecurringPayment.id,
                RecurringPayment.user_id,
                RecurringPayment.title,
                RecurringPayment.amount,
                RecurringPayment.next_due_date,
            )
            .where(
                RecurringPayment.status == "active",
                RecurringPayment.next_due_date <= cutoff_date,
            )
            .order_by(RecurringPayment.next_due_date, RecurringPayment.id)
        )
        if user_id:
            query = query.where(RecurringPayment.user_id == user_id)
        if auto_pay_only:
            query = query.where(RecurringPayment.auto_pay.is_(True))

        # Plain tuples, not ORM objects: they stay readable after a per-item rollback
        due_rows = (await db.execute(query)).all()

        results: list[RecurringTriggerResponse] = []
        skipped = failed = 0
        for payment_id, owner_id, title, amount, due_date in due_rows:
            try:
                results.append(
                    await RecurringService.execute_payment(
                        db=db,
                        user_id=owner_id,
                        payment_id=payment_id,
                        dry_run=dry_run,
                        expected_due_date=due_date,
                    )
                )
                continue
            except HTTPException as exc:
                await db.rollback()
                if exc.status_code == status.HTTP_409_CONFLICT:
                    skipped += 1
                    outcome = "skipped: already processed"
                else:
                    failed += 1
                    outcome = f"error: {exc.detail}"
            except Exception:
                await db.rollback()
                logger.exception("Recurring payment %s failed during batch processing", payment_id)
                failed += 1
                outcome = "error: internal error"

            results.append(
                RecurringTriggerResponse(
                    recurring_payment_id=payment_id,
                    transaction_id=None,
                    title=title,
                    amount=amount,
                    execution_date=due_date,
                    previous_due_date=due_date,
                    new_due_date=due_date,
                    dry_run=dry_run,
                    status=outcome,
                )
            )

        return RecurringBatchTriggerResponse(
            as_of=cutoff_date,
            processed_count=len(results),
            executed_count=len(results) - skipped - failed,
            skipped_count=skipped,
            failed_count=failed,
            dry_run=dry_run,
            results=results,
        )
