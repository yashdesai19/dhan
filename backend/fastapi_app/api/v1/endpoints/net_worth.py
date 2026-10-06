"""API Router for DHAN net worth, account balances, assets and liabilities."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api.deps import get_current_user, get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.net_worth import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    LiabilityCreate,
    LiabilityResponse,
    LiabilityUpdate,
    NetWorthResponse,
)
from fastapi_app.services.net_worth_service import NetWorthService

router = APIRouter(prefix="/net-worth", tags=["Net Worth"])


@router.get("", response_model=NetWorthResponse)
@router.get("/", response_model=NetWorthResponse, include_in_schema=False)
async def get_net_worth(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NetWorthResponse:
    """Net worth, its asset and liability lines, net balance and every account's balance."""
    return await NetWorthService.get_net_worth(db, current_user.id)


@router.get("/history", response_model=list[dict[str, str]])
async def net_worth_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    """Recorded month-end net worth for the user, oldest first."""
    return await NetWorthService.history(db, current_user.id)


@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetResponse]:
    """Assets tracked outside accounts (mutual funds, EPF, gold...)."""
    return await NetWorthService.list_assets(db, current_user.id)


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_in: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    """Start tracking an asset."""
    return await NetWorthService.create_asset(db, current_user.id, asset_in)


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    asset_in: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    """Update an asset, typically its current value."""
    return await NetWorthService.update_asset(db, current_user.id, asset_id, asset_in)


@router.delete("/assets/{asset_id}", response_model=dict[str, str])
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Stop tracking an asset."""
    await NetWorthService.delete_asset(db, current_user.id, asset_id)
    return {"message": "Asset deleted."}


@router.get("/liabilities", response_model=list[LiabilityResponse])
async def list_liabilities(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LiabilityResponse]:
    """Loans tracked outside accounts (credit cards are accounts and appear automatically)."""
    return await NetWorthService.list_liabilities(db, current_user.id)


@router.post("/liabilities", response_model=LiabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_liability(
    liability_in: LiabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LiabilityResponse:
    """Start tracking a loan."""
    return await NetWorthService.create_liability(db, current_user.id, liability_in)


@router.patch("/liabilities/{liability_id}", response_model=LiabilityResponse)
async def update_liability(
    liability_id: uuid.UUID,
    liability_in: LiabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LiabilityResponse:
    """Update a loan, typically what is still owed."""
    return await NetWorthService.update_liability(db, current_user.id, liability_id, liability_in)


@router.delete("/liabilities/{liability_id}", response_model=dict[str, str])
async def delete_liability(
    liability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Stop tracking a loan."""
    await NetWorthService.delete_liability(db, current_user.id, liability_id)
    return {"message": "Liability deleted."}
