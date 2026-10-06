"""Pydantic schemas for DHAN AI conversations and messages."""

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_QUESTION_LENGTH = 2000


class AIConversationCreate(BaseModel):
    title: str | None = Field(
        default=None, max_length=120, description="Defaults to the first question asked"
    )


class AIMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be blank")
        return cleaned


class AIStat(BaseModel):
    label: str
    value: str


class AIMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    seq: int
    role: str = Field(..., description="user or assistant")
    content: str
    intent: str | None = Field(default=None, description="Assistant turns: topic understood")
    stats: list[AIStat] = Field(default_factory=list)
    provider: str | None = Field(default=None, description="Assistant turns: who answered")
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("stats", mode="before")
    @classmethod
    def none_to_empty(cls, v: object) -> object:
        return v or []


class AIConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    message_count: int
    created_at: dt.datetime
    updated_at: dt.datetime


class AIConversationDetail(AIConversationResponse):
    messages: list[AIMessageResponse]


class AIExchangeResponse(BaseModel):
    """A question and its answer, saved together."""

    conversation: AIConversationResponse
    user_message: AIMessageResponse
    assistant_message: AIMessageResponse


class AISuggestionsResponse(BaseModel):
    suggestions: list[str]
