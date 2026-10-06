"""SQLAlchemy model for DHAN Transactions."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.account import Account
    from fastapi_app.models.category import Category
    from fastapi_app.models.user import User


class Transaction(Base):
    """Financial ledger transaction recorded by users (Expense, Income, Transfer)."""

    __tablename__ = "dhan_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_transactions_user_id_5e2c402a_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_accounts.id",
            name="dhan_transactions_account_id_597f27fd_fk_dhan_accounts_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    destination_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_accounts.id",
            name="fk_dhan_transactions_destination_account_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        default=None,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_categories.id",
            name="dhan_transactions_category_id_4ad35949_fk_dhan_categories_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        default=None,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    type: Mapped[str] = mapped_column("transaction_type", String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(
        "date",
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    notes: Mapped[str] = mapped_column("note", Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # For type 'split': the group expense this payment belongs to
    split_expense_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_splits.id", name="fk_dhan_transactions_split_expense_id", ondelete="SET NULL"
        ),
        nullable=True,
        default=None,
    )
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

    # Synonyms for field aliases
    transaction_type = synonym("type")
    date = synonym("transaction_date")
    note = synonym("notes")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="transactions",
    )
    destination_account: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[destination_account_id],
    )
    category: Mapped["Category | None"] = relationship("Category", back_populates="transactions")
