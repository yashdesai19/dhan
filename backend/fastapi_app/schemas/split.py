"""Pydantic schemas for DHAN Splits: Groups, Members, Split Expenses, Settlements, and Balances."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PersonResponse(BaseModel):
    """User representation within split groups and contacts."""

    id: uuid.UUID
    name: str
    email: str
    initials: str
    avatar_tone: str = "primary"

    model_config = ConfigDict(from_attributes=True)


class GroupMemberAdd(BaseModel):
    """Request payload to add a member to a SplitGroup."""

    user_id: uuid.UUID | None = None
    email: str | None = None
    role: str = Field(default="member", pattern=r"^(admin|member)$")


class GroupMemberResponse(BaseModel):
    """Representation of a group member."""

    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(BaseModel):
    """Payload to create a new split group."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    currency: str = Field(default="INR", max_length=3)
    member_ids: list[uuid.UUID] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    """Payload to update an existing group."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    currency: str | None = None


class GroupResponse(BaseModel):
    """Full group details with member listings."""

    id: uuid.UUID
    name: str
    description: str
    about: str | None = None
    currency: str
    created_by_id: uuid.UUID
    members: list[GroupMemberResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SplitItemInput(BaseModel):
    """Individual line item for item-wise splitting."""

    title: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=15)
    member_ids: list[uuid.UUID] = Field(..., min_length=1)


class SplitExpenseCreate(BaseModel):
    """Payload to create a split expense supporting all five splitting methods."""

    group_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=150)
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=15)
    paid_by_id: uuid.UUID | None = None
    split_type: str = Field(
        default="equal",
        pattern=r"^(equal|exact|percentage|shares|itemwise)$",
    )
    display_method: str | None = Field(
        default=None,
        pattern=r"^(equal|exact|percent|shares|itemwise)$",
        description="How the user chose to split, when shares are sent as exact amounts",
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description="Your account the payment came from (only when you paid); moves its balance",
    )
    date: datetime | None = None
    notes: str | None = None

    # Method-specific inputs
    member_ids: list[uuid.UUID] = Field(default_factory=list)
    included: list[uuid.UUID] | None = None
    exact: dict[str, Decimal] | None = None
    percentages: dict[str, Decimal] | None = None
    shares_input: dict[str, Decimal] | None = None
    items: list[SplitItemInput] | None = None


class SplitExpenseUpdate(BaseModel):
    """Payload to modify an existing split expense."""

    title: str | None = Field(default=None, min_length=1, max_length=150)
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=15)
    notes: str | None = None
    date: datetime | None = None


class SplitExpenseResponse(BaseModel):
    """Detailed split expense representation with calculated shares per member."""

    id: uuid.UUID
    group_id: uuid.UUID | None = None
    title: str
    amount: Decimal
    paid_by_id: uuid.UUID
    paid_by_name: str
    split_type: str
    display_method: str | None = None
    shares: dict[str, Decimal]
    date: datetime
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettlementCreate(BaseModel):
    """Payload to record a debt settlement between two members."""

    group_id: uuid.UUID | None = None
    payee_id: uuid.UUID = Field(
        ..., description="The other person: whom you paid, or (direction=received) who paid you"
    )
    amount: Decimal = Field(..., gt=0, decimal_places=2, max_digits=15)
    method: str = Field(default="upi", pattern=r"^(upi|cash|bank)$")
    notes: str | None = None
    direction: str = Field(
        default="paid",
        pattern=r"^(paid|received)$",
        description="paid: you paid them. received: they paid you (only lowers what they owe)",
    )


class SettlementResponse(BaseModel):
    """Settlement payment record between two individuals."""

    id: uuid.UUID
    group_id: uuid.UUID | None = None
    payer_id: uuid.UUID
    payer_name: str
    payee_id: uuid.UUID
    payee_name: str
    amount: Decimal
    status: str
    method: str
    notes: str | None = None
    settled_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonBalance(BaseModel):
    """Net financial balance with an individual peer."""

    user_id: uuid.UUID
    name: str
    email: str
    balance: Decimal  # Positive = they owe you; negative = you owe them


class PositionResponse(BaseModel):
    """Aggregated financial position of the user across split expenses and settlements."""

    owed: Decimal
    owe: Decimal
    net: Decimal
    by_person: dict[str, Decimal]
    people_balances: list[PersonBalance]
