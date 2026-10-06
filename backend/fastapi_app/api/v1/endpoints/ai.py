"""API Router for DHAN AI. Every conversation belongs to, and answers from, the signed-in user."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.ai.providers import AIProvider, get_ai_provider
from fastapi_app.ai.service import SUGGESTIONS, AIService
from fastapi_app.api.deps import get_current_user, get_db
from fastapi_app.core.rate_limit import AI_MESSAGES_PER_USER
from fastapi_app.models.user import User
from fastapi_app.schemas.ai import (
    AIConversationCreate,
    AIConversationDetail,
    AIConversationResponse,
    AIExchangeResponse,
    AIMessageCreate,
    AIMessageResponse,
    AISuggestionsResponse,
)

router = APIRouter(prefix="/ai", tags=["DHAN AI"])


@router.get("/suggestions", response_model=AISuggestionsResponse)
async def suggestions(current_user: User = Depends(get_current_user)) -> AISuggestionsResponse:
    """Questions to offer as chips before the user types."""
    return AISuggestionsResponse(suggestions=SUGGESTIONS)


@router.post(
    "/conversations", response_model=AIConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    conversation_in: AIConversationCreate | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIConversationResponse:
    """Start a conversation (the title defaults to the first question)."""
    title = conversation_in.title if conversation_in else None
    return await AIService.create_conversation(db, current_user.id, title)


@router.get("/conversations", response_model=list[AIConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIConversationResponse]:
    """The user's conversations, most recently active first."""
    return await AIService.list_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500, description="Latest messages to include"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIConversationDetail:
    """A conversation and its history, oldest message first."""
    return await AIService.get_conversation(db, current_user.id, conversation_id, limit)


@router.get("/conversations/{conversation_id}/messages", response_model=list[AIMessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500, description="Latest messages to include"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIMessageResponse]:
    """Conversation history, oldest message first."""
    detail = await AIService.get_conversation(db, current_user.id, conversation_id, limit)
    return detail.messages


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AIExchangeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    message_in: AIMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIExchangeResponse:
    """Ask a question; returns the saved question and DHAN AI's answer."""
    AI_MESSAGES_PER_USER.hit(str(current_user.id))
    return await AIService.send_message(
        db, current_user.id, conversation_id, message_in.content, provider
    )


@router.delete("/conversations/{conversation_id}", response_model=dict[str, str])
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a conversation and all its messages."""
    await AIService.delete_conversation(db, current_user.id, conversation_id)
    return {"message": "Conversation deleted."}
