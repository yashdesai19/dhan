"""SQLAlchemy model for DHAN Budgets."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.category import Category
    from fastapi_app.models.user import User


class Budget(Base):
    """Budget limits allocated per category or overall monthly spending."""

    __tablename__ = "dhan_budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_budgets_user_id_076adbc3_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_categories.id",
            name="dhan_budgets_category_id_eb464729_fk_dhan_categories_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    period: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        server_default="monthly",
        nullable=False,
    )
    month: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    warn_at_percent: Mapped[int] = mapped_column(
        Integer,
        default=90,
        server_default="90",
        nullable=False,
    )
    rollover: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
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

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category | None"] = relationship("Category", back_populates="budgets")
