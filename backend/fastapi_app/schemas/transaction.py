"""Pydantic schemas for DHAN Transactions."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from fastapi_app.core.periods import assume_local


class TransactionBase(BaseModel):
    """Base schema for financial transactions."""

    account_id: uuid.UUID = Field(..., description="Source account ID")
    destination_account_id: uuid.UUID | None = Field(
        default=None, description="Destination account ID (required for transfers)"
    )
    category_id: uuid.UUID | None = Field(default=None, description="Category ID (optional)")
    amount: Decimal = Field(
        ..., gt=Decimal("0.00"), description="Transaction amount (strictly positive Decimal)"
    )
    type: str = Field(..., description="Transaction type: expense, income, transfer")
    description: str = Field(default="", max_length=255, description="Brief description")
    transaction_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution timestamp; without an offset it is read as DHAN local time (IST)",
    )
    notes: str = Field(default="", description="Additional transaction notes")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0.00"):
            raise ValueError("Amount must be strictly greater than 0.00")
        return round(v, 2)

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        clean_type = str(v).lower().strip()
        if clean_type not in {"expense", "income", "transfer"}:
            raise ValueError(
                f"Transaction type must be 'expense', 'income', or 'transfer', got '{v}'"
            )
        return clean_type

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, v: datetime) -> datetime:
        return assume_local(v)

    @model_validator(mode="after")
    def validate_transfer_accounts(self) -> "TransactionBase":
        if self.type == "transfer":
            if self.destination_account_id is None:
                raise ValueError("Transfers require a destination_account_id.")
            if self.destination_account_id == self.account_id:
                raise ValueError("Source account and destination account cannot be the same.")
        elif self.destination_account_id is not None:
            # If not a transfer, destination_account_id should not be set
            self.destination_account_id = None
        return self


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    pass


class TransactionUpdate(BaseModel):
    """Schema for updating an existing transaction (all fields optional)."""

    account_id: uuid.UUID | None = None
    destination_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, gt=Decimal("0.00"))
    type: str | None = None
    description: str | None = Field(default=None, max_length=255)
    transaction_date: datetime | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount_opt(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            if v <= Decimal("0.00"):
                raise ValueError("Amount must be strictly greater than 0.00")
            return round(v, 2)
        return v

    @field_validator("type", mode="before")
    @classmethod
    def validate_type_opt(cls, v: Any) -> str | None:
        if v is None:
            return None
        clean_type = str(v).lower().strip()
        if clean_type not in {"expense", "income", "transfer"}:
            raise ValueError(
                f"Transaction type must be 'expense', 'income', or 'transfer', got '{v}'"
            )
        return clean_type

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date_opt(cls, v: datetime | None) -> datetime | None:
        return assume_local(v) if v is not None else None


class TransactionResponse(BaseModel):
    """API response schema for a transaction."""

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID
    destination_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    amount: Decimal
    type: str
    description: str
    transaction_date: datetime
    notes: str
    is_recurring: bool = False
    split_expense_id: uuid.UUID | None = None
    status: str = "completed"
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transaction_type(self) -> str:
        """Alias matching domain naming."""
        return self.type

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """List response containing transactions and total count."""

    items: list[TransactionResponse]
    total: int
