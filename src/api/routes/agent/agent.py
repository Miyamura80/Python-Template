"""
Agent Route

Authenticated AI agent endpoint using DSPY with tool support.
This endpoint is protected because LLM inference costs can be expensive.
"""

import inspect
import json
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, Iterable, Optional, cast

import dspy
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langfuse.decorators import observe, langfuse_context
from loguru import logger as log
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth.unified_auth import get_authenticated_user_id
from src.api.routes.agent.tools import alert_admin
from src.api.routes.agent.utils import user_uuid_from_str
from src.db.database import get_db_session
from src.db.models.public.agent_conversations import AgentConversation, AgentMessage
from src.utils.logging_config import setup_logging
from utils.llm.dspy_inference import DSPYInference

setup_logging()

router = APIRouter()


class AgentRequest(BaseModel):
    """Request model for agent endpoint."""

    message: str = Field(..., description="User message to the agent")
    context: str | None = Field(
        None, description="Optional additional context for the agent"
    )
    conversation_id: uuid.UUID | None = Field(
        None, description="Existing conversation ID to continue"
    )


class AgentResponse(BaseModel):
    """Response model for agent endpoint."""

    reasoning: str | None = Field(  # noqa: F841
        None, description="Agent's reasoning (if available)"
    )  # noqa
    response: str = Field(..., description="Agent's response")
    user_id: str = Field(..., description="Authenticated user ID")
    conversation_id: uuid.UUID = Field(
        ..., description="Conversation identifier for the interaction"
    )


class AgentSignature(dspy.Signature):
    """Agent signature for processing user messages with tool support."""

    user_id: str = dspy.InputField(desc="The authenticated user ID")
    message: str = dspy.InputField(desc="User's message or question")
    context: str = dspy.InputField(
        desc="Additional context about the user or situation"
    )
    response: str = dspy.OutputField(
        desc="Agent's helpful and comprehensive response to the user"
    )


def get_agent_tools() -> list[Callable[..., Any]]:
    """Return the raw agent tools (unwrapped)."""
    return [alert_admin]


def build_tool_wrappers(
    user_id: str, tools: Optional[Iterable[Callable[..., Any]]] = None
) -> list[Callable[..., Any]]:
    """
    Build tool callables that capture the user context for routing.

    This allows us to return a list of tools, and keeps the wrapping logic
    centralized for both streaming and non-streaming endpoints. Accepts an
    iterable of raw tool functions; defaults to the agent's configured tools.
    """

    raw_tools = list(tools) if tools is not None else get_agent_tools()

    def _wrap_tool(tool: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(tool)
        if "user_id" in signature.parameters:
            return partial(tool, user_id=user_id)
        return tool

    return [_wrap_tool(tool) for tool in raw_tools]


def tool_name(tool: Callable[..., Any]) -> str:
    """Best-effort name for a tool (supports partials)."""
    if hasattr(tool, "__name__"):
        return tool.__name__  # type: ignore[attr-defined]
    func = getattr(tool, "func", None)
    if func and hasattr(func, "__name__"):
        return func.__name__  # type: ignore[attr-defined]
    return "unknown_tool"


def _conversation_title_from_message(message: str) -> str:
    """Generate a short title from the first user message."""
    condensed = " ".join(message.split())
    if len(condensed) > 80:
        return f"{condensed[:80]}..."
    return condensed


def get_or_create_conversation_record(
    db: Session,
    user_uuid: uuid.UUID,
    conversation_id: uuid.UUID | None,
    initial_message: str,
) -> AgentConversation:
    """Fetch an existing conversation or create a new one for the user."""
    if conversation_id:
        conversation = (
            db.query(AgentConversation)
            .filter(
                AgentConversation.id == conversation_id,
                AgentConversation.user_id == user_uuid,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    conversation = AgentConversation(
        user_id=user_uuid, title=_conversation_title_from_message(initial_message)
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def record_agent_message(
    db: Session, conversation: AgentConversation, role: str, content: str
) -> AgentMessage:
    """Persist a single agent message and update conversation timestamp."""
    conversation.updated_at = datetime.now(timezone.utc)
    message = AgentMessage(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(conversation)
    return message


@router.post("/agent", response_model=AgentResponse)  # noqa
@observe()
async def agent_endpoint(
    agent_request: AgentRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AgentResponse:
    """
    Authenticated AI agent endpoint using DSPY with tool support.

    This endpoint processes user messages using an LLM agent that has access
    to various tools to complete tasks. Authentication is required as LLM
    inference can be expensive.

    Available tools:
    - alert_admin: Escalate issues to administrators when the agent cannot help

    Args:
        agent_request: The agent request containing the user's message
        request: FastAPI request object for authentication
        db: Database session

    Returns:
        AgentResponse with the agent's response and metadata

    Raises:
        HTTPException: If authentication fails (401)
    """
    # Authenticate user - will raise 401 if auth fails
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)
    langfuse_context.update_current_observation(name=f"agent-{user_id}")

    log.info(
        f"Agent request from user {user_id}: {agent_request.message[:100]}...",
    )

    try:
        conversation = get_or_create_conversation_record(
            db,
            user_uuid,
            agent_request.conversation_id,
            agent_request.message,
        )
        record_agent_message(db, conversation, "user", agent_request.message)

        # Initialize DSPY inference module with tools
        inference_module = DSPYInference(
            pred_signature=AgentSignature,
            tools=build_tool_wrappers(user_id),
            observe=True,  # Enable LangFuse observability
        )

        # Run agent inference
        result = await inference_module.run(
            user_id=user_id,
            message=agent_request.message,
            context=agent_request.context or "No additional context provided",
        )

        record_agent_message(db, conversation, "assistant", result.response)
        log.info(
            f"Agent response generated for user {user_id} in conversation {conversation.id}"
        )

        return AgentResponse(
            response=result.response,
            user_id=user_id,
            conversation_id=cast(uuid.UUID, conversation.id),
            reasoning=None,  # DSPY ReAct doesn't expose reasoning in the result
        )

    except Exception as e:
        log.error(f"Error processing agent request for user {user_id}: {str(e)}")
        # Return a friendly error response instead of raising
        conversation_id = (
            cast(uuid.UUID, conversation.id)  # type: ignore[name-defined]
            if "conversation" in locals()
            else agent_request.conversation_id or uuid.uuid4()
        )
        return AgentResponse(
            response="I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            user_id=user_id,
            conversation_id=conversation_id,
            reasoning=f"Error: {str(e)}",
        )


@router.post("/agent/stream")  # noqa
@observe()
async def agent_stream_endpoint(
    agent_request: AgentRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """
    Streaming version of the authenticated AI agent endpoint using DSPY.

    This endpoint processes user messages using an LLM agent with streaming
    support, allowing for real-time token-by-token responses. Authentication
    is required as LLM inference can be expensive.

    The response is streamed as Server-Sent Events (SSE) format, with each
    chunk sent as a data line.

    Available tools:
    - alert_admin: Escalate issues to administrators when the agent cannot help

    Args:
        agent_request: The agent request containing the user's message
        request: FastAPI request object for authentication
        db: Database session

    Returns:
        StreamingResponse with text/event-stream content type

    Raises:
        HTTPException: If authentication fails (401)
    """
    # Authenticate user - will raise 401 if auth fails
    user_id = await get_authenticated_user_id(request, db)
    user_uuid = user_uuid_from_str(user_id)
    langfuse_context.update_current_observation(name=f"agent-stream-{user_id}")

    log.info(
        f"Agent streaming request from user {user_id}: {agent_request.message[:100]}..."
    )

    conversation = get_or_create_conversation_record(
        db,
        user_uuid,
        agent_request.conversation_id,
        agent_request.message,
    )
    record_agent_message(db, conversation, "user", agent_request.message)

    async def stream_generator():
        """Generate streaming response chunks."""
        try:
            raw_tools = get_agent_tools()
            tool_functions = build_tool_wrappers(user_id, tools=raw_tools)
            tool_names = [tool_name(tool) for tool in raw_tools]
            response_chunks: list[str] = []

            # Send initial metadata (include tool info for transparency)
            yield f"data: {json.dumps({'type': 'start', 'user_id': user_id, 'conversation_id': str(conversation.id), 'tools_enabled': bool(tool_functions), 'tool_names': tool_names})}\n\n"

            async def stream_with_inference(tools: list):
                """Stream using DSPY with the provided tools list."""
                response_chunks.clear()
                inference_module = DSPYInference(
                    pred_signature=AgentSignature,
                    tools=tools,
                    observe=True,  # Enable LangFuse observability
                )

                async for chunk in inference_module.run_streaming(
                    stream_field="response",
                    user_id=user_id,
                    message=agent_request.message,
                    context=agent_request.context or "No additional context provided",
                ):
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            full_response: str | None = None
            try:
                # Primary path: stream with tools enabled
                async for token_chunk in stream_with_inference(tool_functions):
                    yield token_chunk
                full_response = "".join(response_chunks)
            except Exception as tool_err:
                log.warning(
                    "Streaming with tools failed for user %s, falling back to streaming without tools: %s",
                    user_id,
                    str(tool_err),
                )
                warning_msg = (
                    "Tool-enabled streaming encountered an issue. "
                    "Continuing without tools for this response."
                )
                yield f"data: {json.dumps({'type': 'warning', 'code': 'tool_fallback', 'message': warning_msg})}\n\n"

                # Fallback path: stream without tools to still deliver a response
                async for token_chunk in stream_with_inference([]):
                    yield token_chunk
                full_response = "".join(response_chunks)

            if full_response:
                record_agent_message(db, conversation, "assistant", full_response)

            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            log.info(f"Agent streaming response completed for user {user_id}")

        except Exception as e:
            log.error(
                f"Error processing agent streaming request for user {user_id}: {str(e)}"
            )
            error_msg = (
                "I apologize, but I encountered an error processing your request. "
                "Please try again or contact support if the issue persists."
            )
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
