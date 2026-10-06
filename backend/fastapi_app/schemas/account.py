"""Pydantic schemas for DHAN Accounts."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AccountBase(BaseModel):
    """Base schema for account attributes."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Account name (e.g. HDFC Savings, Cash, Credit Card)",
    )
    type: str = Field(
        "savings",
        description="Account type: savings, bank, cash, wallet, credit_card, investment, other",
    )
    balance: Decimal = Field(default=Decimal("0.00"), description="Account balance")
    currency: str = Field(
        default="INR", min_length=3, max_length=3, description="3-character currency code"
    )
    credit_limit: Decimal | None = Field(
        default=None, ge=0, description="Credit limit for credit cards"
    )
    due_date: int | None = Field(
        default=None, ge=1, le=31, description="Day of month when credit payment is due (1-31)"
    )
    archived: bool = Field(default=False, description="Whether the account is archived")
    include_in_total: bool = Field(
        default=True, description="Whether the balance counts towards net balance and net worth"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Account name cannot be empty or blank")
        return cleaned

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return str(v)

    @model_validator(mode="after")
    def validate_credit_card_rules(self) -> "AccountBase":
        # Validate credit card specifics
        if self.type == "credit_card":
            if self.credit_limit is not None and self.credit_limit < Decimal("0.00"):
                raise ValueError("Credit limit must be a non-negative amount")
        return self


class AccountCreate(AccountBase):
    """Schema for creating a new financial account."""

    institution_name: str = Field(default="", max_length=100)
    account_number_mask: str = Field(default="", max_length=20)


class AccountUpdate(BaseModel):
    """Schema for updating an existing account (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = None
    balance: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    credit_limit: Decimal | None = Field(default=None, ge=0)
    due_date: int | None = Field(default=None, ge=1, le=31)
    archived: bool | None = None
    include_in_total: bool | None = None
    institution_name: str | None = None
    account_number_mask: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_opt(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Account name cannot be empty or blank")
            return cleaned
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency_opt(cls, v: str | None) -> str | None:
        if v is not None:
            return v.upper().strip()
        return v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type_opt(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v).lower().strip()


class AccountResponse(BaseModel):
    """API response schema for an account."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    type: str
    balance: Decimal
    currency: str
    credit_limit: Decimal | None = None
    due_date: int | None = None
    archived: bool
    include_in_total: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountListResponse(BaseModel):
    """List response containing accounts and total count."""

    items: list[AccountResponse]
    total: int
