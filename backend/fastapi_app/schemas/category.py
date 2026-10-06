"""Pydantic schemas for DHAN Categories."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    """Base schema for category attributes."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Category name (e.g. Groceries, Salary)"
    )
    category_type: str = Field("expense", description="Category type: expense, income, transfer")
    icon: str = Field(default="", max_length=50, description="Icon identifier string")
    color: str = Field(default="#4CAF50", max_length=20, description="Hex color string")
    is_active: bool = Field(default=True, description="Whether the category is active")
    ordering: int = Field(default=0, description="Display order ranking")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Category name cannot be empty or blank")
        return cleaned

    @field_validator("category_type", mode="before")
    @classmethod
    def validate_category_type(cls, v: Any) -> str:
        val = str(v).lower().strip()
        if val not in {"expense", "income", "transfer"}:
            raise ValueError(f"category_type must be 'expense', 'income', or 'transfer', got '{v}'")
        return val


class CategoryCreate(CategoryBase):
    """Schema for creating a new custom category."""

    parent_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    category_type: str | None = None
    icon: str | None = None
    color: str | None = None
    is_active: bool | None = None
    ordering: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name_opt(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Category name cannot be empty or blank")
            return cleaned
        return v

    @field_validator("category_type", mode="before")
    @classmethod
    def validate_category_type_opt(cls, v: Any) -> str | None:
        if v is not None:
            val = str(v).lower().strip()
            if val not in {"expense", "income", "transfer"}:
                raise ValueError(
                    f"category_type must be 'expense', 'income', or 'transfer', got '{v}'"
                )
            return val
        return None


class CategoryResponse(BaseModel):
    """API response schema for a category."""

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    name: str
    category_type: str
    icon: str
    color: str
    is_default: bool
    is_active: bool
    ordering: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    """List response containing categories and total count."""

    items: list[CategoryResponse]
    total: int
