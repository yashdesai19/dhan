"""SQLAlchemy models for DHAN Splits: Groups, Members, Split Expenses, and Settlements."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_app.db.base import Base

if TYPE_CHECKING:
    from fastapi_app.models.user import User


class SplitGroup(Base):
    """Collaborative expense splitting groups (e.g. Trips, Flatmates, Projects)."""

    __tablename__ = "dhan_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="INR", server_default="INR", nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_groups_created_by_id_f4045d4d_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
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
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    members: Mapped[list["GroupMember"]] = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    expenses: Mapped[list["SplitExpense"]] = relationship(
        "SplitExpense",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class GroupMember(Base):
    """Membership record linking a User to a SplitGroup."""

    __tablename__ = "dhan_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_dhan_group_members_group_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_groups.id",
            name="fk_dhan_group_members_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_dhan_group_members_user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", server_default="member", nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    group: Mapped["SplitGroup"] = relationship("SplitGroup", back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])


class SplitExpense(Base):
    """Group or peer-to-peer shared expense record with calculated shares."""

    __tablename__ = "dhan_splits"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_groups.id",
            name="dhan_splits_group_id_1f758074_fk_dhan_groups_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_splits_paid_by_id_0396919f_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    split_type: Mapped[str] = mapped_column(
        String(20), default="equal", server_default="equal", nullable=False
    )
    shares: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    split_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    group: Mapped["SplitGroup | None"] = relationship("SplitGroup", back_populates="expenses")
    paid_by: Mapped["User"] = relationship("User", foreign_keys=[paid_by_id])


class Settlement(Base):
    """Payment record resolving debt balances between members."""

    __tablename__ = "dhan_settlements"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "dhan_groups.id",
            name="dhan_settlements_group_id_f35d0946_fk_dhan_groups_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    payer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_settlements_payer_id_36d882e3_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    payee_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="dhan_settlements_payee_id_1ee6f03f_fk_users_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="completed", server_default="completed", nullable=False
    )
    method: Mapped[str] = mapped_column(
        String(20), default="upi", server_default="upi", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    group: Mapped["SplitGroup | None"] = relationship("SplitGroup", back_populates="settlements")
    payer: Mapped["User"] = relationship("User", foreign_keys=[payer_id])
    payee: Mapped["User"] = relationship("User", foreign_keys=[payee_id])
