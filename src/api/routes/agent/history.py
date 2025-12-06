"""Agent chat history routes."""

import uuid
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, Request
from langfuse.decorators import observe, langfuse_context
from loguru import logger as log
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from src.api.auth.unified_auth import get_authenticated_user_id
from src.api.routes.agent.utils import user_uuid_from_str
from src.db.database import get_db_session
from src.db.models.public.agent_conversations import AgentConversation
from src.utils.logging_config import setup_logging

setup_logging()

router = APIRouter()


class AgentMessageModel(BaseModel):
    """Response model for individual chat messages."""

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class AgentConversationModel(BaseModel):
    """Response model for conversations with embedded messages."""

    id: uuid.UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[AgentMessageModel]


class AgentHistoryResponse(BaseModel):
    """Response model for chat history."""

    conversations: list[AgentConversationModel]


def map_conversation_to_model(
    conversation: AgentConversation,
) -> AgentConversationModel:
    """Map ORM conversation with messages to response model."""
    conversation_id = cast(uuid.UUID, conversation.id)
    title = cast(str | None, conversation.title)
    created_at = cast(datetime, conversation.created_at)
    updated_at = cast(datetime, conversation.updated_at)

    return AgentConversationModel(
        id=conversation_id,
        title=title,
        created_at=created_at,
        updated_at=updated_at,
        messages=[
            AgentMessageModel(
                id=cast(uuid.UUID, message.id),
                role=cast(str, message.role),
                content=cast(str, message.content),
                created_at=cast(datetime, message.created_at),
            )
            for message in conversation.messages
        ],
    )


@router.get("/agent/history", response_model=AgentHistoryResponse)  # noqa
@observe()
async def agent_history_endpoint(
    request: Request,
    db: Session = Depends(get_db_session),
) -> AgentHistoryResponse:
    """
    Retrieve authenticated user's past agent conversations with messages.

    This endpoint returns all conversations for the authenticated user,
    including ordered messages within each conversation.
    """

    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)
    langfuse_context.update_current_observation(name=f"agent-history-{user_id}")

    conversations = (
        db.query(AgentConversation)
        .options(selectinload(AgentConversation.messages))
        .filter(AgentConversation.user_id == user_uuid)
        .order_by(AgentConversation.updated_at.desc())
        .all()
    )

    log.info(
        "Fetched %s conversations for user %s",
        len(conversations),
        user_id,
    )

    return AgentHistoryResponse(
        conversations=[map_conversation_to_model(conv) for conv in conversations]
    )
