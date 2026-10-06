"""SQLAlchemy models for DHAN Recurring Payments, Bills, EMIs, and Subscriptions."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.account import Account
    from fastapi_app.models.category import Category
    from fastapi_app.models.user import User


class RecurringPayment(Base):
    """Recurring obligations: Subscriptions, Utility Bills, EMIs, and Periodic Income."""

    __tablename__ = "dhan_recurring_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_recurring_payments_user_id_7e2d179b_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_accounts.id",
            name="dhan_recurring_payments_account_id_fa550fa1_fk_dhan_accounts_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_categories.id",
            name="dhan_recurring_payme_category_id_0e58c3d6_fk_dhan_cate",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(30),
        default="bill",
        server_default="bill",
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        server_default="monthly",
        nullable=False,
    )
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Day of month the schedule is pinned to (1-31). Keeps a bill due on the 31st on the
    # 31st after a short month clips one occurrence to the 28th/30th.
    anchor_day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default="active",
        nullable=False,
    )
    auto_pay: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    last_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="recurring_payments")
    account: Mapped[Account] = relationship("Account", back_populates="recurring_payments")
    category: Mapped[Category | None] = relationship(
        "Category", back_populates="recurring_payments"
    )
