"""FastAPI endpoints for DHAN Splits: Groups, Split Expenses, Settlements, and People."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import require_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.split import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
    PersonResponse,
    PositionResponse,
    SettlementCreate,
    SettlementResponse,
    SplitExpenseCreate,
    SplitExpenseResponse,
    SplitExpenseUpdate,
)
from fastapi_app.services import split_service

groups_router = APIRouter(prefix="/groups", tags=["Groups"])
splits_router = APIRouter(prefix="/splits", tags=["Splits"])
settlements_router = APIRouter(prefix="/settlements", tags=["Settlements"])
people_router = APIRouter(prefix="/people", tags=["People"])


# ---------------------------------------------------------------------------
# Groups Endpoints
# ---------------------------------------------------------------------------


@groups_router.get("", response_model=list[GroupResponse])
@groups_router.get("/", response_model=list[GroupResponse], include_in_schema=False)
async def list_groups(
    response: Response,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GroupResponse]:
    """List all split groups the authenticated user belongs to."""
    items = await split_service.list_groups(db=db, user_id=current_user.id)
    response.headers["X-Total-Count"] = str(len(items))
    return items


@groups_router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
@groups_router.post(
    "/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
async def create_group(
    payload: GroupCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupResponse:
    """Create a new split group."""
    return await split_service.create_group(db=db, user_id=current_user.id, data=payload)


@groups_router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupResponse:
    """Get group details and members list."""
    return await split_service.get_group_by_id(db=db, user_id=current_user.id, group_id=group_id)


@groups_router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupResponse:
    """Update group details (creator only)."""
    return await split_service.update_group(
        db=db, user_id=current_user.id, group_id=group_id, data=payload
    )


@groups_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a split group (creator only)."""
    await split_service.delete_group(db=db, user_id=current_user.id, group_id=group_id)


@groups_router.post(
    "/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED
)
async def add_group_member(
    group_id: uuid.UUID,
    payload: GroupMemberAdd,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GroupMemberResponse:
    """Add a member to the group by user_id or email."""
    return await split_service.add_group_member(
        db=db,
        current_user_id=current_user.id,
        group_id=group_id,
        data=payload,
    )


@groups_router.delete(
    "/{group_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_group_member(
    group_id: uuid.UUID,
    member_user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a member from the group."""
    await split_service.remove_group_member(
        db=db,
        current_user_id=current_user.id,
        group_id=group_id,
        member_user_id=member_user_id,
    )


@groups_router.get("/{group_id}/balances", response_model=PositionResponse)
async def get_group_balances(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PositionResponse:
    """Calculate and return financial balances specifically within this group."""
    # Ensure membership first
    await split_service.get_group_by_id(db=db, user_id=current_user.id, group_id=group_id)
    return await split_service.calculate_balances(
        db=db,
        current_user_id=current_user.id,
        group_id=group_id,
    )


# ---------------------------------------------------------------------------
# Splits (Split Expenses) Endpoints
# ---------------------------------------------------------------------------


@splits_router.get("/balances", response_model=PositionResponse)
async def get_overall_balances(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PositionResponse:
    """Calculate overall financial position and net balances across all groups."""
    return await split_service.calculate_balances(
        db=db,
        current_user_id=current_user.id,
        group_id=None,
    )


@splits_router.get("", response_model=list[SplitExpenseResponse])
@splits_router.get("/", response_model=list[SplitExpenseResponse], include_in_schema=False)
async def list_split_expenses(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SplitExpenseResponse]:
    """Split expenses in the user's groups or involving the user, newest first."""
    return await split_service.list_split_expenses(db=db, current_user_id=current_user.id)


@splits_router.post("", response_model=SplitExpenseResponse, status_code=status.HTTP_201_CREATED)
@splits_router.post(
    "/",
    response_model=SplitExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_split_expense(
    payload: SplitExpenseCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SplitExpenseResponse:
    """Create a shared expense split using any of the 5 methods (equal, exact, percentage, shares, itemwise)."""
    return await split_service.create_split_expense(
        db=db,
        current_user_id=current_user.id,
        data=payload,
    )


@splits_router.get("/{expense_id}", response_model=SplitExpenseResponse)
async def get_split_expense(
    expense_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SplitExpenseResponse:
    """Retrieve details and calculated shares for a split expense."""
    return await split_service.get_split_expense(
        db=db,
        current_user_id=current_user.id,
        expense_id=expense_id,
    )


@splits_router.patch("/{expense_id}", response_model=SplitExpenseResponse)
async def update_split_expense(
    expense_id: uuid.UUID,
    payload: SplitExpenseUpdate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SplitExpenseResponse:
    """Update title, notes, or date of a split expense."""
    return await split_service.update_split_expense(
        db=db,
        current_user_id=current_user.id,
        expense_id=expense_id,
        data=payload,
    )


@splits_router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_split_expense(
    expense_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a split expense."""
    await split_service.delete_split_expense(
        db=db,
        current_user_id=current_user.id,
        expense_id=expense_id,
    )


# ---------------------------------------------------------------------------
# Settlements Endpoints
# ---------------------------------------------------------------------------


@settlements_router.get("", response_model=list[SettlementResponse])
@settlements_router.get("/", response_model=list[SettlementResponse], include_in_schema=False)
async def list_settlements(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SettlementResponse]:
    """Settlements the user paid or received, newest first."""
    return await split_service.list_settlements(db=db, current_user_id=current_user.id)


@settlements_router.delete("/{settlement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_settlement(
    settlement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Undo a settlement you paid or received."""
    await split_service.delete_settlement(
        db=db, current_user_id=current_user.id, settlement_id=settlement_id
    )


@settlements_router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
@settlements_router.post(
    "/",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_settlement(
    payload: SettlementCreate,
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettlementResponse:
    """Record a debt settlement payment between two peers."""
    return await split_service.create_settlement(
        db=db,
        current_user_id=current_user.id,
        data=payload,
    )


# ---------------------------------------------------------------------------
# People Endpoints
# ---------------------------------------------------------------------------


@people_router.get("", response_model=list[PersonResponse])
@people_router.get("/", response_model=list[PersonResponse], include_in_schema=False)
async def list_people(
    current_user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PersonResponse]:
    """List people/contacts available to the user for expense splits."""
    return await split_service.list_people(db=db, current_user_id=current_user.id)
