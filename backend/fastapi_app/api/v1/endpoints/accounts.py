"""FastAPI endpoints for DHAN Accounts."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from fastapi_app.services import account_service

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=list[AccountResponse])
@router.get("/", response_model=list[AccountResponse], include_in_schema=False)
async def list_accounts(
    response: Response,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = Query(default=False, description="Include archived accounts"),
    account_type: str | None = Query(default=None, description="Filter by account type"),
    limit: int = Query(default=100, ge=1, le=500, description="Pagination limit"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> list[AccountResponse]:
    """Retrieve all accounts owned by the authenticated user."""
    items, total = await account_service.list_accounts(
        db=db,
        user_id=current_user.id,
        include_archived=include_archived,
        account_type=account_type,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [AccountResponse.model_validate(item) for item in items]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_account(
    payload: AccountCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Create a new account owned by the authenticated user."""
    account = await account_service.create_account(
        db=db,
        user_id=current_user.id,
        data=payload,
    )
    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Retrieve a specific account by ID, strictly enforcing ownership."""
    account = await account_service.get_account(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
    )
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Update an existing account owned by the authenticated user."""
    account = await account_service.update_account(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        data=payload,
    )
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}", response_model=AccountResponse)
async def delete_or_archive_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard: bool = Query(
        default=False, description="Set True to permanently delete instead of archive"
    ),
) -> AccountResponse | Response:
    """Archive (soft-delete) or permanently delete an account owned by user."""
    account = await account_service.archive_or_delete_account(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        hard_delete=hard,
    )
    if account is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return AccountResponse.model_validate(account)


@router.post("/{account_id}/archive", response_model=AccountResponse)
async def archive_account_action(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountResponse:
    """Explicitly archive an account owned by the user."""
    account = await account_service.archive_or_delete_account(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        hard_delete=False,
    )
    assert account is not None
    return AccountResponse.model_validate(account)
