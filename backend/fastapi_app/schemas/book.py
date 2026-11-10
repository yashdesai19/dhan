"""Pydantic schemas for DHAN Books."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookCreate(BaseModel):
    """Schema for creating a business book."""

    name: str = Field(..., min_length=1, max_length=60)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Book name cannot be empty or blank")
        return cleaned


class BookResponse(BaseModel):
    """API response schema for a book."""

    id: uuid.UUID
    name: str
    kind: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
