"""
Ping Route

Simple ping endpoint for frontend connectivity testing.
"""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class PingResponse(BaseModel):
    """Response for ping endpoint."""

    message: str  # noqa: vulture
    status: str  # noqa: vulture
    timestamp: str


@router.get("/ping", response_model=PingResponse)  # noqa
async def ping() -> PingResponse:
    """Simple ping endpoint for frontend connectivity testing."""
    return PingResponse(
        message="pong",
        status="ok",
        timestamp=datetime.now().isoformat(),
    )
