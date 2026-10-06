"""FastAPI endpoints for DHAN Transactions."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from fastapi_app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
@router.get("/", response_model=list[TransactionResponse], include_in_schema=False)
async def list_transactions(
    response: Response,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    account_id: uuid.UUID | None = Query(default=None, description="Filter by account ID"),
    category_id: uuid.UUID | None = Query(default=None, description="Filter by category ID"),
    type: str | None = Query(
        default=None, description="Filter by transaction type (expense, income, transfer)"
    ),
    start_date: datetime | None = Query(
        default=None, description="Filter transactions on/after date"
    ),
    end_date: datetime | None = Query(
        default=None, description="Filter transactions on/before date"
    ),
    search: str | None = Query(default=None, description="Search description and notes"),
    sort_by: str = Query(default="date", description="Sort field: date, amount, created_at"),
    sort_order: str = Query(default="desc", description="Sort direction: asc or desc"),
    limit: int = Query(default=100, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> list[TransactionResponse]:
    """Retrieve transactions for the authenticated user with filtering, sorting, and pagination."""
    items, total = await transaction_service.list_transactions(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [TransactionResponse.model_validate(item) for item in items]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_transaction(
    payload: TransactionCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """Record a new financial transaction (expense, income, transfer) and atomically update balances."""
    tx = await transaction_service.create_transaction(
        db=db,
        user_id=current_user.id,
        data=payload,
    )
    return TransactionResponse.model_validate(tx)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """Retrieve a single transaction by ID ensuring user ownership."""
    tx = await transaction_service.get_transaction(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return TransactionResponse.model_validate(tx)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionResponse:
    """Update an existing transaction and atomically adjust balances if financial amounts change."""
    tx = await transaction_service.update_transaction(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
        data=payload,
    )
    return TransactionResponse.model_validate(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a transaction and atomically revert its financial impact on account balances."""
    await transaction_service.delete_transaction(
        db=db,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
