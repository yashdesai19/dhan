"""Service layer for DHAN net worth (mirrors utils/netWorth.ts and netBalance in utils/summary.ts).

Every query filters on the requesting user's id; records owned by someone else are reported as
not found rather than forbidden, so their existence isn't revealed either.
"""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.core.periods import get_timezone, today_in
from fastapi_app.models.account import Account
from fastapi_app.models.net_worth import Asset, Liability, NetWorthSnapshot
from fastapi_app.schemas.net_worth import (
    AccountBalance,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    LiabilityCreate,
    LiabilityResponse,
    LiabilityUpdate,
    NetBalance,
    NetWorthResponse,
    NetWorthRow,
)

ZERO = Decimal("0.00")

BANK_TYPES = {"bank", "savings"}
INVESTMENT_TYPES = {"investment"}
CREDIT_TYPES = {"credit_card", "credit"}


def account_group(account: Account) -> str:
    """banks, investments, credit, or cash (cash, wallet and anything custom, as in the app)."""
    if account.type in BANK_TYPES:
        return "banks"
    if account.type in INVESTMENT_TYPES:
        return "investments"
    if account.type in CREDIT_TYPES:
        return "credit"
    return "cash"


def is_counted(account: Account) -> bool:
    """Whether an account's balance counts towards net balance and net worth."""
    return account.include_in_total and not account.archived


def _sum(accounts: Iterable[Account]) -> Decimal:
    return sum((a.balance for a in accounts), ZERO)


def _group_row(row_id: str, name: str, accounts: list[Account]) -> NetWorthRow:
    return NetWorthRow(
        id=row_id,
        source="accounts",
        name=name,
        value=_sum(accounts),
        account_names=[a.name for a in accounts],
    )


async def _get_owned[Record: (Asset, Liability)](
    db: AsyncSession, model: type[Record], user_id: uuid.UUID, record_id: uuid.UUID
) -> Record:
    stmt = select(model).where(model.id == record_id, model.user_id == user_id)
    record = (await db.execute(stmt)).scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found or access denied.",
        )
    return record


class NetWorthService:
    """Account balances, net balance, and net worth from accounts, assets and liabilities."""

    @staticmethod
    async def get_net_worth(db: AsyncSession, user_id: uuid.UUID) -> NetWorthResponse:
        """Spec §6: net worth = assets - liabilities.

        Assets: bank accounts, cash and wallets, investment accounts, any credit card in credit,
        and tracked assets. Liabilities: what's owed on each credit card, and tracked loans.
        """
        accounts = (
            (
                await db.execute(
                    select(Account)
                    .where(Account.user_id == user_id, Account.archived.is_(False))
                    .order_by(Account.created_at, Account.name)
                )
            )
            .scalars()
            .all()
        )
        assets = (
            (
                await db.execute(
                    select(Asset)
                    .where(Asset.user_id == user_id)
                    .order_by(Asset.created_at, Asset.name)
                )
            )
            .scalars()
            .all()
        )
        liabilities = (
            (
                await db.execute(
                    select(Liability)
                    .where(Liability.user_id == user_id)
                    .order_by(Liability.created_at, Liability.name)
                )
            )
            .scalars()
            .all()
        )

        counted = [a for a in accounts if is_counted(a)]
        groups: dict[str, list[Account]] = {
            "banks": [],
            "cash": [],
            "investments": [],
            "credit": [],
        }
        for account in counted:
            groups[account_group(account)].append(account)
        cards = groups["credit"]

        asset_rows = [
            _group_row("banks", "Bank accounts", groups["banks"]),
            _group_row("cash", "Cash and wallets", groups["cash"]),
        ]
        if groups["investments"]:
            asset_rows.append(
                _group_row("investments", "Investment accounts", groups["investments"])
            )
        # A card paid beyond its balance is money the bank owes the user
        cards_in_credit = [a for a in cards if a.balance > 0]
        if cards_in_credit:
            asset_rows.append(_group_row("card_credit", "Card credit", cards_in_credit))
        asset_rows += [
            NetWorthRow(
                id=str(asset.id),
                source="asset",
                name=asset.name,
                type=asset.asset_type,
                value=asset.current_value,
                updated_at=asset.updated_at,
            )
            for asset in assets
        ]

        liability_rows = [
            NetWorthRow(
                id=str(card.id),
                source="credit_card",
                name=card.name,
                type="credit_card",
                value=max(ZERO, -card.balance),
                due_day=card.due_date,
            )
            for card in cards
        ]
        liability_rows += [
            NetWorthRow(
                id=str(loan.id),
                source="liability",
                name=loan.name,
                type=loan.liability_type,
                value=loan.remaining_amount,
                due_date=loan.due_date,
                updated_at=loan.updated_at,
            )
            for loan in liabilities
        ]

        total_assets = sum((r.value for r in asset_rows), ZERO)
        total_liabilities = sum((r.value for r in liability_rows), ZERO)
        await NetWorthService._record_snapshot(db, user_id, total_assets - total_liabilities)
        return NetWorthResponse(
            assets=asset_rows,
            liabilities=liability_rows,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=total_assets - total_liabilities,
            net_balance=NetBalance(total=_sum(counted), count=len(counted)),
            accounts=[
                AccountBalance(
                    id=a.id, name=a.name, type=a.type, balance=a.balance, included=is_counted(a)
                )
                for a in accounts
            ],
        )

    @staticmethod
    async def _record_snapshot(db: AsyncSession, user_id: uuid.UUID, value: Decimal) -> None:
        """Keeps this month's net worth, so past months have real values instead of estimates."""
        month = today_in(get_timezone()).strftime("%Y-%m")
        stmt = insert(NetWorthSnapshot).values(
            id=uuid.uuid4(), user_id=user_id, month=month, net_worth=value
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_dhan_net_worth_snapshots_user_month",
            set_={"net_worth": value, "updated_at": datetime.now(UTC)},
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def history(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, str]]:
        """Recorded month-end net worth, oldest first."""
        res = await db.execute(
            select(NetWorthSnapshot.month, NetWorthSnapshot.net_worth)
            .where(NetWorthSnapshot.user_id == user_id)
            .order_by(NetWorthSnapshot.month)
        )
        return [{"month": m, "net_worth": str(v)} for m, v in res.all()]

    # ------------------------------------------------------------------ assets

    @staticmethod
    async def list_assets(db: AsyncSession, user_id: uuid.UUID) -> list[AssetResponse]:
        stmt = select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at, Asset.name)
        return [AssetResponse.model_validate(a) for a in (await db.execute(stmt)).scalars()]

    @staticmethod
    async def create_asset(
        db: AsyncSession, user_id: uuid.UUID, asset_in: AssetCreate
    ) -> AssetResponse:
        asset = Asset(user_id=user_id, **asset_in.model_dump())
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return AssetResponse.model_validate(asset)

    @staticmethod
    async def update_asset(
        db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID, asset_in: AssetUpdate
    ) -> AssetResponse:
        asset = await _get_owned(db, Asset, user_id, asset_id)
        changes = asset_in.model_dump(exclude_unset=True)
        for field in ("name", "asset_type", "current_value"):
            if changes.get(field, ...) is None:
                changes.pop(field)  # required columns: null means "leave as is"
        for field, value in changes.items():
            setattr(asset, field, value)
        asset.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(asset)
        return AssetResponse.model_validate(asset)

    @staticmethod
    async def delete_asset(db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID) -> None:
        asset = await _get_owned(db, Asset, user_id, asset_id)
        await db.delete(asset)
        await db.commit()

    # ------------------------------------------------------------- liabilities

    @staticmethod
    async def list_liabilities(db: AsyncSession, user_id: uuid.UUID) -> list[LiabilityResponse]:
        stmt = (
            select(Liability)
            .where(Liability.user_id == user_id)
            .order_by(Liability.created_at, Liability.name)
        )
        return [LiabilityResponse.model_validate(x) for x in (await db.execute(stmt)).scalars()]

    @staticmethod
    async def create_liability(
        db: AsyncSession, user_id: uuid.UUID, liability_in: LiabilityCreate
    ) -> LiabilityResponse:
        liability = Liability(user_id=user_id, **liability_in.model_dump())
        db.add(liability)
        await db.commit()
        await db.refresh(liability)
        return LiabilityResponse.model_validate(liability)

    @staticmethod
    async def update_liability(
        db: AsyncSession,
        user_id: uuid.UUID,
        liability_id: uuid.UUID,
        liability_in: LiabilityUpdate,
    ) -> LiabilityResponse:
        liability = await _get_owned(db, Liability, user_id, liability_id)
        changes = liability_in.model_dump(exclude_unset=True)
        for field in ("name", "liability_type", "total_amount", "remaining_amount"):
            if changes.get(field, ...) is None:
                changes.pop(field)  # required columns: null means "leave as is"
        total = changes.get("total_amount", liability.total_amount)
        remaining = changes.get("remaining_amount", liability.remaining_amount)
        if remaining > total:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="remaining_amount cannot exceed total_amount",
            )
        for field, value in changes.items():
            setattr(liability, field, value)
        liability.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(liability)
        return LiabilityResponse.model_validate(liability)

    @staticmethod
    async def delete_liability(
        db: AsyncSession, user_id: uuid.UUID, liability_id: uuid.UUID
    ) -> None:
        liability = await _get_owned(db, Liability, user_id, liability_id)
        await db.delete(liability)
        await db.commit()
