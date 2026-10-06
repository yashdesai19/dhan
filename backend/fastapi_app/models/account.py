"""SQLAlchemy model for DHAN Accounts."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.recurring import RecurringPayment
    from fastapi_app.models.transaction import Transaction
    from fastapi_app.models.user import User


class Account(Base):
    """Financial account owned by a user (e.g. HDFC Savings, SBI Savings, Cash, Paytm, Credit Card)."""

    __tablename__ = "dhan_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_accounts_user_id_ce900dec_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column("account_type", String(30), default="savings", nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    institution_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    account_number_mask: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Counted in net balance and net worth (the app's "Include in total" switch)
    include_in_total: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    credit_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True, default=None
    )
    due_date: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    account_type = synonym("type")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.account_id",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    recurring_payments: Mapped[list["RecurringPayment"]] = relationship(
        "RecurringPayment",
        back_populates="account",
        cascade="all, delete-orphan",
    )
