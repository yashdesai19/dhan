"""SQLAlchemy models for DHAN net worth: assets and liabilities held outside accounts.

Both tables were created by the Django admin's initial migration; these models map them as is.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.db.base import Base


class Asset(Base):
    """Something the user owns that isn't an account: mutual funds, EPF, gold, property."""

    __tablename__ = "dhan_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_assets_user_id_b938bcde_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Liability(Base):
    """A debt that isn't a credit card account: home loan, vehicle loan, personal loan."""

    __tablename__ = "dhan_liabilities"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_liabilities_user_id_2e175ff7_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    liability_type: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    # What is still owed; this is the figure net worth subtracts
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    monthly_emi: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class NetWorthSnapshot(Base):
    """A user's net worth as last seen in a month; the latest view in a month is its value."""

    __tablename__ = "dhan_net_worth_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_dhan_net_worth_snapshots_user_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_dhan_net_worth_snapshots_user_id", ondelete="CASCADE"),
        nullable=False,
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
