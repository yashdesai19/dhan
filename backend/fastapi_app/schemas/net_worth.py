"""Pydantic schemas for DHAN net worth, account balances, assets and liabilities."""

import datetime as dt
import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ASSET_TYPE_PATTERN = "^(stock|mutual_fund|epf|crypto|real_estate|gold|fixed_deposit|cash|other)$"
LIABILITY_TYPE_PATTERN = "^(mortgage|auto_loan|personal_loan|credit_card|student_loan|other)$"


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="e.g. Mutual funds, Gold")
    asset_type: str = Field(..., pattern=ASSET_TYPE_PATTERN)
    current_value: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    purchase_date: dt.date | None = None


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    asset_type: str | None = Field(default=None, pattern=ASSET_TYPE_PATTERN)
    current_value: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    purchase_date: dt.date | None = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    asset_type: str
    current_value: Decimal
    purchase_price: Decimal | None = None
    purchase_date: dt.date | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class LiabilityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="e.g. Bike loan")
    liability_type: str = Field(..., pattern=LIABILITY_TYPE_PATTERN)
    total_amount: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    remaining_amount: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    interest_rate: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    monthly_emi: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    due_date: dt.date | None = None

    @model_validator(mode="after")
    def remaining_within_total(self) -> "LiabilityCreate":
        if self.remaining_amount > self.total_amount:
            raise ValueError("remaining_amount cannot exceed total_amount")
        return self


class LiabilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    liability_type: str | None = Field(default=None, pattern=LIABILITY_TYPE_PATTERN)
    total_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    remaining_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    interest_rate: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    monthly_emi: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    due_date: dt.date | None = None


class LiabilityResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    liability_type: str
    total_amount: Decimal
    remaining_amount: Decimal
    interest_rate: Decimal | None = None
    monthly_emi: Decimal | None = None
    due_date: dt.date | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class AccountBalance(BaseModel):
    """One account as it stands now."""

    id: uuid.UUID
    name: str
    type: str
    balance: Decimal
    included: bool = Field(..., description="Counted in net balance (not archived, included)")


class NetBalance(BaseModel):
    """Sum of the balances of counted accounts; credit card debt counts as negative."""

    total: Decimal
    count: int


class NetWorthRow(BaseModel):
    """A line on the net worth screen."""

    id: str = Field(..., description="'banks', 'cash', 'investments', 'card_credit' or a record id")
    source: str = Field(..., description="accounts, credit_card, asset or liability")
    name: str
    type: str | None = Field(
        default=None, description="Asset or liability type, where there is one"
    )
    value: Decimal
    account_names: list[str] = Field(default_factory=list)
    due_day: int | None = Field(default=None, description="Credit card bill day of month")
    due_date: dt.date | None = None
    updated_at: dt.datetime | None = None


class NetWorthResponse(BaseModel):
    """Spec §6: net worth = assets - liabilities, from accounts plus tracked assets and loans."""

    assets: list[NetWorthRow]
    liabilities: list[NetWorthRow]
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    net_balance: NetBalance
    accounts: list[AccountBalance]
