"""
Unified Authentication Module

This module provides flexible authentication that supports multiple authentication methods:
- WorkOS JWT tokens (Authorization: Bearer header)
- API keys (X-API-KEY header)

The authentication logic tries JWT first, then falls back to API key authentication.
"""

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from loguru import logger

from src.api.auth.api_key_auth import get_current_user_from_api_key_header
from src.api.auth.workos_auth import get_current_workos_user
from src.utils.logging_config import setup_logging

# Setup logging at module import
setup_logging()


async def get_authenticated_user_id(request: Request, db_session: Session) -> str:
    """
    Flexible authentication that supports both WorkOS JWT and API key authentication.

    Tries JWT authentication first (Authorization header), then falls back to API key (X-API-KEY header).

    Args:
        request: FastAPI request object
        db_session: Database session (for future use with API keys)

    Returns:
        user_id string if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    # Try WorkOS JWT authentication first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        try:
            workos_user = await get_current_workos_user(request)
            logger.info(f"User authenticated via WorkOS JWT: {workos_user.id}")
            return workos_user.id
        except HTTPException as e:
            logger.warning(f"WorkOS JWT authentication failed: {e.detail}")
            # Continue to try API key authentication if implemented
        except Exception as e:
            logger.warning(f"Unexpected error in WorkOS JWT authentication: {e}")
            # Continue to try API key authentication if implemented

    # Try API key authentication (if header is present)
    api_key = request.headers.get("X-API-KEY")
    if api_key:
        try:
            user_id = await get_current_user_from_api_key_header(request, db_session)
            logger.info(f"User authenticated via API key: {user_id}")
            return user_id
        except HTTPException as e:
            logger.warning(f"API key authentication failed: {e.detail}")
        except Exception as e:
            logger.warning(f"Unexpected error in API key authentication: {e}")

    # If we get here, authentication failed
    raise HTTPException(
        status_code=401,
        detail=(
            "Authentication required. Provide "
            "'Authorization: Bearer <workos_token>' or 'X-API-KEY' header"
        ),
    )
