"""DHAN AI service: conversations, history, and answering a question.

Mobile -> FastAPI (/ai) -> AIService -> AIProvider

AIService owns everything a provider must not: who the user is, which conversation is theirs,
and what data may be read. Every query here filters on the authenticated user's id, and the
provider only sees the facts UserFinanceReader gathered for that user.
"""

import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.ai.context import UserFinanceReader
from fastapi_app.ai.intents import classify, resolve_month
from fastapi_app.ai.providers import (
    AIProvider,
    AIProviderUnavailable,
    HistoryTurn,
    ProviderReply,
    ProviderRequest,
)
from fastapi_app.core.config import settings
from fastapi_app.core.periods import get_timezone, today_in
from fastapi_app.models.ai import AIConversation, AIMessage
from fastapi_app.schemas.ai import (
    AIConversationDetail,
    AIConversationResponse,
    AIExchangeResponse,
    AIMessageResponse,
)

logger = logging.getLogger(__name__)

TITLE_LENGTH = 60

SUGGESTIONS = [
    "How much did I spend this month?",
    "Where did most of my money go?",
    "Am I within my budget?",
    "What are my recent expenses?",
    "How are my goals doing?",
    "What bills are coming up?",
    "What's my net worth?",
    "What's my account balance?",
]


def title_from(question: str) -> str:
    """A conversation title from its first question, cut at a word boundary."""
    text = " ".join(question.split())
    if len(text) <= TITLE_LENGTH:
        return text
    return text[: TITLE_LENGTH - 1].rsplit(" ", 1)[0] + "…"


async def _get_owned(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, *, for_update: bool = False
) -> AIConversation:
    """The user's conversation, else 404 (whether it doesn't exist or belongs to someone else)."""
    stmt = select(AIConversation).where(
        AIConversation.id == conversation_id, AIConversation.user_id == user_id
    )
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    conversation = (await db.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return conversation


def _messages_of(user_id: uuid.UUID, conversation_id: uuid.UUID) -> Select[AIMessage]:
    return select(AIMessage).where(
        AIMessage.conversation_id == conversation_id, AIMessage.user_id == user_id
    )


def _summary(conversation: AIConversation, message_count: int) -> AIConversationResponse:
    return AIConversationResponse(
        id=conversation.id,
        title=conversation.title,
        message_count=message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


class AIService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession, user_id: uuid.UUID, title: str | None = None
    ) -> AIConversationResponse:
        conversation = AIConversation(user_id=user_id, title=(title or "").strip())
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return _summary(conversation, 0)

    @staticmethod
    async def list_conversations(
        db: AsyncSession, user_id: uuid.UUID
    ) -> list[AIConversationResponse]:
        """The user's conversations, most recently active first."""
        stmt = (
            select(AIConversation, func.count(AIMessage.id))
            .outerjoin(AIMessage, AIMessage.conversation_id == AIConversation.id)
            .where(AIConversation.user_id == user_id)
            .group_by(AIConversation.id)
            .order_by(AIConversation.updated_at.desc(), AIConversation.id)
        )
        return [_summary(c, count) for c, count in (await db.execute(stmt)).all()]

    @staticmethod
    async def get_conversation(
        db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 100
    ) -> AIConversationDetail:
        """A conversation with its latest `limit` messages, oldest first."""
        conversation = await _get_owned(db, user_id, conversation_id)
        count = await db.scalar(
            select(func.count()).select_from(_messages_of(user_id, conversation_id).subquery())
        )
        latest = (
            (
                await db.execute(
                    _messages_of(user_id, conversation_id)
                    .order_by(AIMessage.seq.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return AIConversationDetail(
            **_summary(conversation, count or 0).model_dump(),
            messages=[AIMessageResponse.model_validate(m) for m in reversed(latest)],
        )

    @staticmethod
    async def delete_conversation(
        db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> None:
        conversation = await _get_owned(db, user_id, conversation_id)
        await db.delete(conversation)
        await db.commit()

    @staticmethod
    async def send_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        question: str,
        provider: AIProvider,
    ) -> AIExchangeResponse:
        """Answers a question from the user's own data and saves both turns.

        Nothing is saved if the provider fails, so the client can simply retry.
        """
        await _get_owned(db, user_id, conversation_id)
        earlier = (
            (
                await db.execute(
                    _messages_of(user_id, conversation_id)
                    .order_by(AIMessage.seq.desc())
                    .limit(settings.AI_HISTORY_LIMIT)
                )
            )
            .scalars()
            .all()
        )
        history = [HistoryTurn(role=m.role, content=m.content) for m in reversed(earlier)]

        tz = get_timezone()
        today = today_in(tz)
        intent = classify(question)
        reader = UserFinanceReader(db, user_id, tz, today)
        facts = await reader.facts_for(intent, resolve_month(question, today))
        request = ProviderRequest(question=question, intent=intent, facts=facts, history=history)

        # End the read transaction first: a hosted model may take seconds, and shouldn't hold a
        # pooled connection or any lock while it does.
        await db.rollback()
        asked_at = datetime.now(UTC)
        reply = await AIService._generate(provider, request)

        # Re-lock to number the turns; also catches the conversation being deleted meanwhile
        conversation = await _get_owned(db, user_id, conversation_id, for_update=True)
        last_seq = int(
            await db.scalar(
                select(func.coalesce(func.max(AIMessage.seq), 0)).where(
                    AIMessage.conversation_id == conversation_id
                )
            )
            or 0
        )
        user_message = AIMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            seq=last_seq + 1,
            role="user",
            content=question,
            created_at=asked_at,
        )
        assistant_message = AIMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            seq=last_seq + 2,
            role="assistant",
            content=reply.content,
            intent=intent.value,
            stats=[asdict(stat) for stat in reply.stats],
            provider=provider.name,
            created_at=datetime.now(UTC),
        )
        db.add_all([user_message, assistant_message])
        if not conversation.title:
            conversation.title = title_from(question)
        conversation.updated_at = datetime.now(UTC)
        await db.commit()

        return AIExchangeResponse(
            # Turns are never deleted one by one, so the last seq is the message count
            conversation=_summary(conversation, assistant_message.seq),
            user_message=AIMessageResponse.model_validate(user_message),
            assistant_message=AIMessageResponse.model_validate(assistant_message),
        )

    @staticmethod
    async def _generate(provider: AIProvider, request: ProviderRequest) -> ProviderReply:
        try:
            return await provider.generate(request)
        except AIProviderUnavailable:
            raise
        except Exception as exc:
            logger.exception("AI provider %s failed", provider.name)
            raise AIProviderUnavailable(
                "DHAN AI couldn't answer right now. Please try again."
            ) from exc
