"""User model for DHAN authentication and authorization."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from fastapi_app.models.account import Account
    from fastapi_app.models.budget import Budget
    from fastapi_app.models.category import Category
    from fastapi_app.models.goal import Goal
    from fastapi_app.models.recurring import RecurringPayment
    from fastapi_app.models.token import RefreshToken
    from fastapi_app.models.transaction import Transaction


class User(Base, TimestampMixin):
    """DHAN unified user account representing normal users and administrators."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    goals: Mapped[list["Goal"]] = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recurring_payments: Mapped[list["RecurringPayment"]] = relationship(
        "RecurringPayment",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def is_admin(self) -> bool:
        """Helper to verify if the user possesses admin privileges."""
        return self.role == "admin"

    def is_active(self) -> bool:
        """Helper to verify if the user account is active."""
        return self.status == "active"
