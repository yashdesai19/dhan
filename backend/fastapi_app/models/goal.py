"""SQLAlchemy models for DHAN Goals and Goal Contributions."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.account import Account
    from fastapi_app.models.user import User


class Goal(Base):
    """Financial savings targets set by users."""

    __tablename__ = "dhan_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_goals_user_id_5359bf57_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    icon: Mapped[str] = mapped_column(
        String(50), default="target", server_default="target", nullable=False
    )
    target_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="in_progress",
        server_default="in_progress",
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
    user: Mapped[User] = relationship("User", back_populates="goals")
    contributions: Mapped[list[GoalContribution]] = relationship(
        "GoalContribution",
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalContribution.date.desc(), GoalContribution.created_at.desc()",
    )


class GoalContribution(Base):
    """Individual financial contributions toward reaching a specific goal."""

    __tablename__ = "dhan_goal_contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dhan_goals.id", name="fk_dhan_goal_contributions_goal_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_dhan_goal_contributions_user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_accounts.id",
            name="fk_dhan_goal_contributions_account_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    goal: Mapped[Goal] = relationship("Goal", back_populates="contributions")
    user: Mapped[User] = relationship("User")
    account: Mapped[Account | None] = relationship("Account")
