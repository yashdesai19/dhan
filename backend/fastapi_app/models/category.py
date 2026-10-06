"""SQLAlchemy model for DHAN Categories."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.budget import Budget
    from fastapi_app.models.recurring import RecurringPayment
    from fastapi_app.models.transaction import Transaction
    from fastapi_app.models.user import User


class Category(Base):
    """Expense and Income categories for transactions (system default or user-owned)."""

    __tablename__ = "dhan_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_dhan_categories_user_id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str] = mapped_column(String(20), default="expense", nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_categories.id",
            name="dhan_categories_parent_id_b8d9e0e8_fk_dhan_categories_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
        default=None,
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordering: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    type = synonym("category_type")

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="category",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        back_populates="category",
    )
    recurring_payments: Mapped[list["RecurringPayment"]] = relationship(
        "RecurringPayment",
        back_populates="category",
    )
