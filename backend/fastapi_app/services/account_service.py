"""Business logic and database service for DHAN Accounts."""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.models.account import Account
from fastapi_app.schemas.account import AccountCreate, AccountUpdate


async def create_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: AccountCreate,
) -> Account:
    """Create a new financial account for the authenticated user."""
    # Check for duplicate account name for this user (case-insensitive)
    query = select(Account).where(
        Account.user_id == user_id,
        func.lower(Account.name) == data.name.lower().strip(),
        Account.archived.is_(False),
    )
    result = await db.execute(query)
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active account named '{data.name}' already exists.",
        )

    # Validate credit card specifics
    if data.type == "credit_card":
        if data.due_date is not None and not (1 <= data.due_date <= 31):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Credit card due date must be an integer between 1 and 31.",
            )
        if data.credit_limit is not None and data.credit_limit < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Credit card credit limit cannot be negative.",
            )

    account = Account(
        user_id=user_id,
        name=data.name,
        type=data.type,
        balance=data.balance,
        currency=data.currency,
        credit_limit=data.credit_limit,
        due_date=data.due_date,
        archived=data.archived,
        is_active=not data.archived,
        include_in_total=data.include_in_total,
        institution_name=data.institution_name,
        account_number_mask=data.account_number_mask,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def get_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Account:
    """Retrieve an account ensuring strict user ownership."""
    query = select(Account).where(Account.id == account_id)
    result = await db.execute(query)
    account = result.scalars().first()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    # Strictly enforce ownership: User A cannot access User B's account
    if account.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    return account


async def list_accounts(
    db: AsyncSession,
    user_id: uuid.UUID,
    include_archived: bool = False,
    account_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Account], int]:
    """List accounts for the authenticated user with optional archived filtering and pagination."""
    query = select(Account).where(Account.user_id == user_id)

    if not include_archived:
        query = query.where(Account.archived.is_(False))

    if account_type:
        query = query.where(Account.type == account_type.lower().strip())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate and order
    query = query.order_by(Account.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total_count


async def update_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    data: AccountUpdate,
) -> Account:
    """Update an existing account verifying user ownership."""
    account = await get_account(db=db, user_id=user_id, account_id=account_id)

    # If renaming, ensure name uniqueness for this user
    if data.name is not None and data.name.lower().strip() != account.name.lower():
        dup_query = select(Account).where(
            Account.user_id == user_id,
            func.lower(Account.name) == data.name.lower().strip(),
            Account.id != account_id,
            Account.archived.is_(False),
        )
        existing = (await db.execute(dup_query)).scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An active account named '{data.name}' already exists.",
            )
        account.name = data.name

    if data.type is not None:
        account.type = data.type

    if data.balance is not None:
        account.balance = data.balance

    if data.currency is not None:
        account.currency = data.currency

    if data.credit_limit is not None:
        if data.credit_limit < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Credit limit cannot be negative.",
            )
        account.credit_limit = data.credit_limit

    if data.due_date is not None:
        if not (1 <= data.due_date <= 31):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Due date must be between 1 and 31.",
            )
        account.due_date = data.due_date

    if data.archived is not None:
        account.archived = data.archived
        account.is_active = not data.archived

    if data.include_in_total is not None:
        account.include_in_total = data.include_in_total

    if data.institution_name is not None:
        account.institution_name = data.institution_name

    if data.account_number_mask is not None:
        account.account_number_mask = data.account_number_mask

    await db.commit()
    await db.refresh(account)
    return account


async def archive_or_delete_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    hard_delete: bool = False,
) -> Account | None:
    """Archive (soft-delete) or hard-delete an account owned by user."""
    account = await get_account(db=db, user_id=user_id, account_id=account_id)

    if hard_delete:
        await db.delete(account)
        await db.commit()
        return None

    account.archived = True
    account.is_active = False
    await db.commit()
    await db.refresh(account)
    return account
