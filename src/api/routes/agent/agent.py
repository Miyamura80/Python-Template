"""
Agent Route

Authenticated AI agent endpoint using DSPY with tool support.
This endpoint is protected because LLM inference costs can be expensive.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import dspy
from loguru import logger as log
import json

from src.api.auth.unified_auth import get_authenticated_user_id
from src.db.database import get_db_session
from src.utils.logging_config import setup_logging
from utils.llm.dspy_inference import DSPYInference
from langfuse.decorators import observe, langfuse_context

# Import available tools
from src.api.routes.agent.tools import alert_admin

setup_logging()

router = APIRouter()


class AgentRequest(BaseModel):
    """Request model for agent endpoint."""

    message: str = Field(..., description="User message to the agent")
    context: str | None = Field(
        None, description="Optional additional context for the agent"
    )


class AgentResponse(BaseModel):
    """Response model for agent endpoint."""

    response: str = Field(..., description="Agent's response")
    user_id: str = Field(..., description="Authenticated user ID")
    reasoning: str | None = Field(
        None, description="Agent's reasoning (if available)"
    )  # noqa


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
    langfuse_context.update_current_observation(name=f"agent-{user_id}")

    log.info(f"Agent request from user {user_id}: {agent_request.message[:100]}...")

    try:
        # Initialize DSPY inference with tools
        # Note: The alert_admin tool needs to be wrapped to match DSPY's expectations
        def alert_admin_tool(issue_description: str, user_context: str = None) -> dict:
            """
            Alert administrators when the agent cannot complete a task.
            Use this as a last resort when all other approaches fail.

            Args:
                issue_description: Clear description of what cannot be accomplished
                user_context: Optional additional context about the situation

            Returns:
                dict: Status of the alert operation
            """
            return alert_admin(
                user_id=user_id,
                issue_description=issue_description,
                user_context=user_context,
            )

        # Initialize DSPY inference module with tools
        inference_module = DSPYInference(
            pred_signature=AgentSignature,
            tools=[alert_admin_tool],
            observe=True,  # Enable LangFuse observability
        )

        # Run agent inference
        result = await inference_module.run(
            user_id=user_id,
            message=agent_request.message,
            context=agent_request.context or "No additional context provided",
        )

        log.info(f"Agent response generated for user {user_id}")

        return AgentResponse(
            response=result.response,
            user_id=user_id,
            reasoning=None,  # DSPY ReAct doesn't expose reasoning in the result
        )

    except Exception as e:
        log.error(f"Error processing agent request for user {user_id}: {str(e)}")
        # Return a friendly error response instead of raising
        return AgentResponse(
            response="I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            user_id=user_id,
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
    langfuse_context.update_current_observation(name=f"agent-stream-{user_id}")

    log.info(
        f"Agent streaming request from user {user_id}: {agent_request.message[:100]}..."
    )

    async def stream_generator():
        """Generate streaming response chunks."""
        try:
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'start', 'user_id': user_id})}\n\n"

            # Note: Tool use with streaming is complex and may not work reliably
            # For now, we'll use streaming without tools
            # If tools are needed, consider using the non-streaming endpoint

            # Initialize DSPY inference module without tools for streaming
            inference_module = DSPYInference(
                pred_signature=AgentSignature,
                tools=[],  # Streaming with tools is not yet fully supported
                observe=True,  # Enable LangFuse observability
            )

            # Stream the response
            async for chunk in inference_module.run_streaming(
                stream_field="response",
                user_id=user_id,
                message=agent_request.message,
                context=agent_request.context or "No additional context provided",
            ):
                # Send each chunk as SSE data
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

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
