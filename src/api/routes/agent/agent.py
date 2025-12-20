"""
Agent Route

Authenticated AI agent endpoint using DSPY with tool support.
This endpoint is protected because LLM inference costs can be expensive.
"""

import asyncio
import inspect
import json
import queue as queue_module
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional, Protocol, Sequence, cast

import dspy
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from loguru import logger as log
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from common import global_config
from src.api.auth.unified_auth import get_authenticated_user
from src.api.routes.agent.tools import alert_admin
from src.api.auth.utils import user_uuid_from_str
from src.api.limits import ensure_daily_limit
from src.db.database import get_db_session
from src.db.utils.db_transaction import db_transaction, scoped_session
from src.db.models.public.agent_conversations import AgentConversation, AgentMessage
from src.utils.logging_config import setup_logging
from utils.llm.dspy_inference import DSPYInference
from utils.llm.tool_streaming_callback import ToolStreamingCallback

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


class ConversationMessage(BaseModel):
    """Single message within a conversation snapshot."""

    role: str
    content: str
    created_at: datetime


class ConversationPayload(BaseModel):
    """Conversation snapshot containing title and ordered messages."""

    id: uuid.UUID
    title: str
    updated_at: datetime
    conversation: list[ConversationMessage]


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
    conversation: ConversationPayload | None = Field(
        None,
        description=(
            "Snapshot of the conversation including title and back-and-forth messages"
        ),
    )


class AgentSignature(dspy.Signature):
    """Agent signature for processing user messages with tool support."""

    user_id: str = dspy.InputField(desc="The authenticated user ID")
    message: str = dspy.InputField(desc="User's message or question")
    context: str = dspy.InputField(
        desc="Additional context about the user or situation"
    )
    history: list[dict[str, str]] = dspy.InputField(
        desc="Ordered conversation history as role/content pairs (oldest to newest)"
    )
    response: str = dspy.OutputField(
        desc="Agent's helpful and comprehensive response to the user"
    )


class MessageLike(Protocol):
    role: str
    content: str


def get_agent_tools() -> list[Callable[..., Any]]:
    """Return the raw agent tools (unwrapped)."""
    return [alert_admin]


def get_history_limit() -> int:
    """Return configured history window for agent context."""
    try:
        return int(getattr(global_config.agent_chat, "history_message_limit", 20))
    except Exception:
        return 20


def fetch_recent_messages(
    db: Session, conversation_id: uuid.UUID, history_limit: int
) -> list[AgentMessage]:
    """Fetch recent messages for a conversation in chronological order."""
    if history_limit <= 0:
        return []

    messages = (
        db.query(AgentMessage)
        .filter(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.created_at.desc())
        .limit(history_limit)
        .all()
    )

    return list(reversed(messages))


def serialize_history(
    messages: Sequence[Any], history_limit: int
) -> list[dict[str, str]]:
    """Convert message models into role/content pairs for LLM context."""
    if history_limit <= 0:
        return []

    recent_messages = list(messages)[-history_limit:]
    return [
        {
            "role": str(getattr(message, "role", "")),
            "content": str(getattr(message, "content", "")),
        }
        for message in recent_messages
    ]


def build_tool_wrappers(
    user_id: str, tools: Optional[Iterable[Callable[..., Any]]] = None
) -> list[Callable[..., Any]]:
    """
    Build tool callables that capture the user context for routing.

    This allows us to return a list of tools, and keeps the wrapping logic
    centralized for both streaming and non-streaming endpoints. Accepts an
    iterable of raw tool functions; defaults to the agent's configured tools.

    IMPORTANT: We use functools.wraps to preserve __name__ and __doc__ attributes
    so that DSPY's ReAct can properly identify and describe the tools to the LLM.
    Without this, partial() creates a callable named "partial" with no docstring,
    making the tool invisible to the agent.
    """
    from functools import wraps
    import re

    raw_tools = list(tools) if tools is not None else get_agent_tools()

    def _wrap_tool(tool: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(tool)
        if "user_id" in signature.parameters:
            # Create a wrapper that preserves metadata instead of using partial
            @wraps(tool)
            def wrapped_tool(*args: Any, **kwargs: Any) -> Any:
                kwargs["user_id"] = user_id
                return tool(*args, **kwargs)

            # Explicitly copy over important attributes that DSPY looks for
            # Note: @wraps copies these, but we ensure they're set for DSPY introspection
            wrapped_tool.__name__ = getattr(tool, "__name__", "unknown_tool")  # type: ignore[attr-defined]

            # Modify the docstring to remove user_id parameter documentation
            # This prevents the LLM from being confused about whether to pass user_id
            original_doc = getattr(tool, "__doc__", None)
            if original_doc:
                # Remove the user_id line from Args section
                modified_doc = re.sub(
                    r"\s*user_id:.*?\n", "", original_doc, flags=re.IGNORECASE
                )
                wrapped_tool.__doc__ = modified_doc  # type: ignore[attr-defined]
            else:
                wrapped_tool.__doc__ = None  # type: ignore[attr-defined]

            # Update the signature to remove user_id (it's now injected)
            new_params = [
                p for name, p in signature.parameters.items() if name != "user_id"
            ]
            wrapped_tool.__signature__ = signature.replace(parameters=new_params)  # type: ignore[attr-defined]

            return wrapped_tool
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


def build_conversation_payload(
    conversation: AgentConversation,
    messages: Sequence[AgentMessage],
    history_limit: int,
) -> ConversationPayload:
    """Create a conversation payload limited to the configured history window."""
    if history_limit <= 0:
        trimmed_messages: list[AgentMessage] = []
    else:
        trimmed_messages = list(messages)[-history_limit:]

    return ConversationPayload(
        id=cast(uuid.UUID, conversation.id),
        title=str(conversation.title) if conversation.title else "Untitled chat",
        updated_at=cast(datetime, conversation.updated_at),
        conversation=[
            ConversationMessage(
                role=cast(str, message.role),
                content=cast(str, message.content),
                created_at=cast(datetime, message.created_at),
            )
            for message in trimmed_messages
        ],
    )


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
    with db_transaction(db):
        db.add(conversation)
    db.refresh(conversation)
    return conversation


def record_agent_message(
    db: Session, conversation: AgentConversation, role: str, content: str
) -> AgentMessage:
    """Persist a single agent message and update conversation timestamp."""
    conversation.updated_at = datetime.now(timezone.utc)
    message = AgentMessage(conversation_id=conversation.id, role=role, content=content)
    with db_transaction(db):
        db.add(message)
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
    auth_user = await get_authenticated_user(request, db)
    user_id = auth_user.id
    user_uuid = user_uuid_from_str(user_id)
    span_name = f"agent-{auth_user.email}" if auth_user.email else f"agent-{user_id}"
    langfuse_context.update_current_observation(name=span_name)

    limit_status = ensure_daily_limit(db=db, user_uuid=user_uuid, enforce=True)
    log.info(
        f"Agent request from user {user_id}: {agent_request.message[:100]}...",
    )
    log.debug(
        "Daily chat usage for user %s: %s used, %s remaining (tier=%s)",
        user_id,
        limit_status.used_today,
        limit_status.remaining,
        limit_status.tier,
    )

    try:
        conversation = get_or_create_conversation_record(
            db,
            user_uuid,
            agent_request.conversation_id,
            agent_request.message,
        )
        record_agent_message(db, conversation, "user", agent_request.message)
        history_limit = get_history_limit()
        history_messages = fetch_recent_messages(
            db,
            cast(uuid.UUID, conversation.id),
            history_limit,
        )
        history_payload = serialize_history(history_messages, history_limit)

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
            history=history_payload,
        )

        assistant_message = record_agent_message(
            db,
            conversation,
            "assistant",
            result.response,
        )
        history_with_assistant = [*history_messages, assistant_message]
        conversation_snapshot = build_conversation_payload(
            conversation, history_with_assistant, history_limit
        )
        log.info(
            f"Agent response generated for user {user_id} in conversation {conversation.id}"
        )

        return AgentResponse(
            response=result.response,
            user_id=user_id,
            conversation_id=cast(uuid.UUID, conversation.id),
            conversation=conversation_snapshot,
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
            response=(
                "I apologize, but I encountered an error processing your request. "
                "Please try again or contact support if the issue persists."
            ),
            user_id=user_id,
            conversation_id=conversation_id,
            reasoning=f"Error: {str(e)}",
        )


@router.post("/agent/stream")  # noqa
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
    auth_user = await get_authenticated_user(request, db)
    user_id = auth_user.id
    user_uuid = user_uuid_from_str(user_id)
    span_name = (
        f"agent-stream-{auth_user.email}"
        if auth_user.email
        else f"agent-stream-{user_id}"
    )

    limit_status = ensure_daily_limit(db=db, user_uuid=user_uuid, enforce=True)
    log.debug(
        f"Agent streaming request from user {user_id}: {agent_request.message[:100]}..."
    )
    log.debug(
        "Daily chat usage for user %s: %s used, %s remaining (tier=%s)",
        user_id,
        limit_status.used_today,
        limit_status.remaining,
        limit_status.tier,
    )

    conversation = get_or_create_conversation_record(
        db,
        user_uuid,
        agent_request.conversation_id,
        agent_request.message,
    )
    record_agent_message(db, conversation, "user", agent_request.message)
    history_limit = get_history_limit()
    history_messages = fetch_recent_messages(
        db,
        cast(uuid.UUID, conversation.id),
        history_limit,
    )
    history_payload = serialize_history(history_messages, history_limit)
    conversation_title = conversation.title or "Untitled chat"
    conversation_id = cast(uuid.UUID, conversation.id)

    # IMPORTANT: Close the DB session BEFORE starting the streaming generator
    # This prevents holding a DB connection during the entire streaming operation
    db.close()

    async def stream_generator():
        """Generate streaming response chunks.

        Note: This generator opens a NEW database session only when needed
        to avoid holding connections during long streaming operations.
        """
        # Create a Langfuse trace for the entire streaming operation
        langfuse_client = Langfuse()
        trace = langfuse_client.trace(name=span_name, user_id=user_id)
        trace_id = trace.id

        # Track last activity time for heartbeat mechanism
        last_activity_time = asyncio.get_event_loop().time()
        heartbeat_interval = (
            global_config.agent_chat.streaming.heartbeat_interval_seconds
        )

        async def maybe_send_heartbeat():
            """Send heartbeat if enough time has passed since last activity."""
            nonlocal last_activity_time
            current_time = asyncio.get_event_loop().time()
            if current_time - last_activity_time >= heartbeat_interval:
                # SSE comments (lines starting with ':') are ignored by clients
                # but keep the connection alive
                last_activity_time = current_time
                return ": heartbeat\n\n"
            return None

        try:
            raw_tools = get_agent_tools()
            tool_functions = build_tool_wrappers(user_id, tools=raw_tools)
            tool_names = [tool_name(tool) for tool in raw_tools]
            response_chunks: list[str] = []

            # Send initial metadata (include tool info for transparency)
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "start",
                        "user_id": user_id,
                        "conversation_id": str(conversation_id),
                        "conversation_title": conversation_title,
                        "tools_enabled": bool(tool_functions),
                        "tool_names": tool_names,
                    }
                )
                + "\n\n"
            )
            last_activity_time = (
                asyncio.get_event_loop().time()
            )  # Reset after sending data

            event_queue: queue_module.Queue[dict[str, Any] | None] = (
                queue_module.Queue()
            )
            internal_full_response: str | None = None
            internal_error: str | None = None

            def push_event(payload: dict[str, Any]) -> None:
                event_queue.put(payload)

            async def worker_async() -> None:
                """
                Run DSPy inference (including tool calls) in a dedicated event loop.

                This allows the SSE writer to remain responsive and flush tool lifecycle
                events to the client in real-time even if tools block.
                """
                try:
                    worker_chunks: list[str] = []

                    async def stream_with_inference(
                        tools: list[Callable[..., Any]],
                    ) -> None:
                        inference_module = DSPYInference(
                            pred_signature=AgentSignature,
                            tools=tools,
                            observe=True,  # Enable LangFuse observability
                            trace_id=trace_id,  # Pass trace context for proper nesting
                            extra_callbacks=[
                                ToolStreamingCallback(event_sink=push_event)
                            ],
                        )

                        async for chunk in inference_module.run_streaming(
                            stream_field="response",
                            user_id=user_id,
                            message=agent_request.message,
                            context=agent_request.context
                            or "No additional context provided",
                            history=history_payload,
                        ):
                            worker_chunks.append(chunk)
                            push_event({"type": "token", "content": chunk})

                    try:
                        await stream_with_inference(tool_functions)
                    except Exception as tool_err:
                        log.warning(
                            "Streaming with tools failed for user %s, falling back to streaming without tools: %s",
                            user_id,
                            str(tool_err),
                        )
                        push_event(
                            {
                                "type": "warning",
                                "code": "tool_fallback",
                                "message": (
                                    "Tool-enabled streaming encountered an issue. "
                                    "Continuing without tools for this response."
                                ),
                            }
                        )
                        worker_chunks.clear()
                        await stream_with_inference([])

                    full_response = "".join(worker_chunks)
                    if not full_response:
                        log.warning(
                            "Streaming produced no tokens for user %s; running non-streaming fallback",
                            user_id,
                        )
                        fallback_inference = DSPYInference(
                            pred_signature=AgentSignature,
                            tools=tool_functions,
                            observe=True,
                            trace_id=trace_id,
                            extra_callbacks=[
                                ToolStreamingCallback(event_sink=push_event)
                            ],
                        )
                        result = await fallback_inference.run(
                            user_id=user_id,
                            message=agent_request.message,
                            context=agent_request.context
                            or "No additional context provided",
                            history=history_payload,
                        )
                        full_response = result.response
                        push_event({"type": "token", "content": full_response})

                    push_event({"_internal": "final", "full_response": full_response})
                except Exception as e:
                    push_event({"_internal": "error", "error": str(e)})
                finally:
                    event_queue.put(None)

            def worker_entrypoint() -> None:
                try:
                    asyncio.run(worker_async())
                except Exception as e:
                    push_event({"_internal": "error", "error": str(e)})
                    event_queue.put(None)

            worker_thread = threading.Thread(target=worker_entrypoint, daemon=True)
            worker_thread.start()

            # Drain events from the worker thread with a short timeout so we can keep
            # sending heartbeats while the agent is thinking/using tools.
            while True:
                try:
                    item = await asyncio.to_thread(event_queue.get, True, 0.25)
                except queue_module.Empty:
                    heartbeat = await maybe_send_heartbeat()
                    if heartbeat:
                        yield heartbeat
                    continue

                if item is None:
                    break

                if item.get("_internal") == "final":
                    full_value = item.get("full_response")
                    internal_full_response = (
                        str(full_value) if full_value is not None else None
                    )
                    continue

                if item.get("_internal") == "error":
                    err_value = item.get("error")
                    internal_error = (
                        str(err_value) if err_value is not None else "unknown"
                    )
                    continue

                if item.get("type") == "token":
                    response_chunks.append(str(item.get("content", "")))

                yield "data: " + json.dumps(item) + "\n\n"
                last_activity_time = asyncio.get_event_loop().time()

            if internal_error:
                raise RuntimeError(internal_error)

            full_response = internal_full_response or "".join(response_chunks)

            if full_response:
                # Open a NEW database session just for this write operation
                with scoped_session() as write_db:
                    # Fetch the conversation again in this new session
                    conversation_obj = (
                        write_db.query(AgentConversation)
                        .filter(AgentConversation.id == conversation_id)
                        .first()
                    )
                    if conversation_obj:
                        assistant_message = record_agent_message(
                            write_db, conversation_obj, "assistant", full_response
                        )
                        history_messages.append(assistant_message)
                        conversation_snapshot = build_conversation_payload(
                            conversation_obj, history_messages, history_limit
                        )
                    else:
                        log.error(
                            f"Conversation {conversation_id} not found after streaming!"
                        )
                        conversation_snapshot = None
                if conversation_snapshot:
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "conversation",
                                "conversation": conversation_snapshot.model_dump(
                                    mode="json"
                                ),
                            }
                        )
                        + "\n\n"
                    )

            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            log.debug(f"Agent streaming response completed for user {user_id}")

            # Finalize the trace with success status
            trace.update(
                output={
                    "status": "completed",
                    "response_length": len(full_response or ""),
                }
            )

        except Exception as e:
            log.error(
                f"Error processing agent streaming request for user {user_id}: {str(e)}"
            )
            error_msg = (
                "I apologize, but I encountered an error processing your request. "
                "Please try again or contact support if the issue persists."
            )
            # Update trace with error status
            trace.update(output={"status": "error", "error": str(e)})
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        finally:
            # Ensure Langfuse flushes the trace in the background
            # We run this in a background task to avoid blocking the response
            async def flush_langfuse():
                """Flush Langfuse in a background task to avoid blocking."""
                try:
                    # Run the blocking flush in a thread pool to avoid blocking event loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, langfuse_client.flush)
                    log.debug("Langfuse flush completed in background")
                except Exception as e:
                    log.error(f"Error flushing Langfuse: {e}")

            # Schedule the flush but don't wait for it
            asyncio.create_task(flush_langfuse())

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
