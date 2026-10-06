"""Business logic, financial calculations, and database transactions for DHAN Transactions."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.periods import assume_local
from fastapi_app.models.account import Account
from fastapi_app.models.category import Category
from fastapi_app.models.transaction import Transaction
from fastapi_app.schemas.transaction import TransactionCreate, TransactionUpdate


async def _get_account_for_update(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Fetch an account with a row-level lock (FOR UPDATE) ensuring user ownership."""
    query = (
        select(Account)
        .where(Account.id == account_id, Account.user_id == user_id)
        .with_for_update()
    )
    result = await db.execute(query)
    account = result.scalars().first()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found or does not belong to user.",
        )
    return account


def _refuse_split(tx: Transaction) -> None:
    """A group-expense payment changes with its group expense, never on its own."""
    if tx.type == "split":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This payment belongs to a group expense. Change or delete it in Splits.",
        )


async def _validate_category(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None,
) -> None:
    """Verify that a category exists and is accessible to the user (owned or system default)."""
    if category_id is None:
        return
    query = select(Category).where(
        Category.id == category_id,
        or_(
            Category.user_id == user_id,
            Category.user_id.is_(None),
            Category.is_default.is_(True),
        ),
    )
    result = await db.execute(query)
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category_id}' not found or is inaccessible.",
        )


async def create_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: TransactionCreate,
) -> Transaction:
    """Atomically record a transaction and apply financial balance updates."""
    clean_type = data.type.lower().strip()
    if clean_type not in {"expense", "income", "transfer"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid transaction type '{data.type}'. Must be 'expense', 'income', or 'transfer'.",
        )

    if data.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction amount must be strictly positive.",
        )

    # Validate category accessibility
    await _validate_category(db, user_id, data.category_id)

    # Financial operations under database transaction
    source_acc = await _get_account_for_update(db, user_id, data.account_id)

    if clean_type == "expense":
        # Expense decreases account balance
        source_acc.balance = Decimal(str(source_acc.balance)) - data.amount
        dest_account_id = None

    elif clean_type == "income":
        # Income increases account balance
        source_acc.balance = Decimal(str(source_acc.balance)) + data.amount
        dest_account_id = None

    elif clean_type == "transfer":
        # Transfer decreases source and increases destination
        if not data.destination_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfers require a destination account.",
            )
        if data.destination_account_id == data.account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source account and destination account cannot be the same.",
            )

        dest_acc = await _get_account_for_update(db, user_id, data.destination_account_id)
        source_acc.balance = Decimal(str(source_acc.balance)) - data.amount
        dest_acc.balance = Decimal(str(dest_acc.balance)) + data.amount
        dest_account_id = data.destination_account_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported transaction type '{clean_type}'",
        )

    tx = Transaction(
        user_id=user_id,
        account_id=data.account_id,
        destination_account_id=dest_account_id,
        category_id=data.category_id,
        amount=data.amount,
        type=clean_type,
        description=data.description,
        transaction_date=data.transaction_date,
        notes=data.notes,
        status="completed",
        is_recurring=False,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def get_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction:
    """Retrieve a single transaction strictly enforcing user ownership."""
    query = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(query)
    tx = result.scalars().first()

    if tx is None or tx.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found.",
        )
    return tx


async def list_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    transaction_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    """List transactions for the authenticated user with filtering, search, sorting, and pagination."""
    query = select(Transaction).where(Transaction.user_id == user_id)

    if account_id:
        query = query.where(
            or_(
                Transaction.account_id == account_id,
                Transaction.destination_account_id == account_id,
            )
        )

    if category_id:
        query = query.where(Transaction.category_id == category_id)

    if transaction_type:
        query = query.where(Transaction.type == transaction_type.lower().strip())

    if start_date:
        query = query.where(Transaction.transaction_date >= assume_local(start_date))

    if end_date:
        query = query.where(Transaction.transaction_date <= assume_local(end_date))

    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Transaction.description).like(search_term),
                func.lower(Transaction.notes).like(search_term),
            )
        )

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Sorting
    sort_column: Any = Transaction.transaction_date
    if sort_by == "amount":
        sort_column = Transaction.amount
    elif sort_by == "created_at":
        sort_column = Transaction.created_at

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(desc(sort_column))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total_count


async def delete_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> None:
    """Delete a transaction and atomically revert its financial balance impact."""
    tx = await get_transaction(db=db, user_id=user_id, transaction_id=transaction_id)
    _refuse_split(tx)

    if tx.type == "expense":
        # Reversing expense: restore money to account
        source_acc = await _get_account_for_update(db, user_id, tx.account_id)
        source_acc.balance = Decimal(str(source_acc.balance)) + tx.amount

    elif tx.type == "income":
        # Reversing income: deduct money from account
        source_acc = await _get_account_for_update(db, user_id, tx.account_id)
        source_acc.balance = Decimal(str(source_acc.balance)) - tx.amount

    elif tx.type == "transfer":
        # Reversing transfer: refund source, deduct destination
        source_acc = await _get_account_for_update(db, user_id, tx.account_id)
        assert tx.destination_account_id is not None
        dest_acc = await _get_account_for_update(db, user_id, tx.destination_account_id)
        source_acc.balance = Decimal(str(source_acc.balance)) + tx.amount
        dest_acc.balance = Decimal(str(dest_acc.balance)) - tx.amount

    await db.delete(tx)
    await db.commit()


async def update_transaction(
    db: AsyncSession,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
) -> Transaction:
    """Update a transaction, atomically adjusting account balances if financial attributes change."""
    tx = await get_transaction(db=db, user_id=user_id, transaction_id=transaction_id)
    _refuse_split(tx)

    # Check if financial attributes are being updated
    financial_update_requested = (
        data.amount is not None
        or data.type is not None
        or data.account_id is not None
        or data.destination_account_id is not None
    )

    if financial_update_requested:
        # Step 1: Revert old financial effect
        if tx.type == "expense":
            old_source = await _get_account_for_update(db, user_id, tx.account_id)
            old_source.balance = Decimal(str(old_source.balance)) + tx.amount
        elif tx.type == "income":
            old_source = await _get_account_for_update(db, user_id, tx.account_id)
            old_source.balance = Decimal(str(old_source.balance)) - tx.amount
        elif tx.type == "transfer":
            old_source = await _get_account_for_update(db, user_id, tx.account_id)
            assert tx.destination_account_id is not None
            old_dest = await _get_account_for_update(db, user_id, tx.destination_account_id)
            old_source.balance = Decimal(str(old_source.balance)) + tx.amount
            old_dest.balance = Decimal(str(old_dest.balance)) - tx.amount

        # Step 2: Resolve target financial values
        target_type = data.type.lower().strip() if data.type else tx.type
        target_amount = data.amount if data.amount is not None else tx.amount
        target_source_id = data.account_id if data.account_id else tx.account_id
        target_dest_id = (
            data.destination_account_id
            if data.destination_account_id is not None
            else tx.destination_account_id
        )

        if target_amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transaction amount must be strictly positive.",
            )

        # Step 3: Apply new financial effect
        if target_type == "expense":
            new_source = await _get_account_for_update(db, user_id, target_source_id)
            new_source.balance = Decimal(str(new_source.balance)) - target_amount
            tx.destination_account_id = None
        elif target_type == "income":
            new_source = await _get_account_for_update(db, user_id, target_source_id)
            new_source.balance = Decimal(str(new_source.balance)) + target_amount
            tx.destination_account_id = None
        elif target_type == "transfer":
            if not target_dest_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transfers require a destination account.",
                )
            if target_source_id == target_dest_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Source account and destination account cannot be the same.",
                )
            new_source = await _get_account_for_update(db, user_id, target_source_id)
            new_dest = await _get_account_for_update(db, user_id, target_dest_id)
            new_source.balance = Decimal(str(new_source.balance)) - target_amount
            new_dest.balance = Decimal(str(new_dest.balance)) + target_amount
            tx.destination_account_id = target_dest_id

        tx.type = target_type
        tx.amount = target_amount
        tx.account_id = target_source_id

    # Update non-financial attributes
    if data.category_id is not None:
        await _validate_category(db, user_id, data.category_id)
        tx.category_id = data.category_id

    if data.description is not None:
        tx.description = data.description

    if data.transaction_date is not None:
        tx.transaction_date = data.transaction_date

    if data.notes is not None:
        tx.notes = data.notes

    await db.commit()
    await db.refresh(tx)
    return tx
