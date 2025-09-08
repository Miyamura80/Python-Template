"""
Unified Authentication Module

This module provides flexible authentication that supports multiple authentication methods:
- Supabase JWT tokens (Authorization: Bearer header)
- API keys (X-API-KEY header)

The authentication logic tries JWT first, then falls back to API key authentication.
"""

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from loguru import logger

from src.api.auth.supabase_jwt import get_current_supabase_user
from src.middleware.auth_middleware import get_current_user_from_api_key_header


async def get_authenticated_user_id(
    request: Request, db_session: Session
) -> str:
    """
    Flexible authentication that supports both Supabase JWT and API key authentication.
    
    Tries JWT authentication first (Authorization header), then falls back to API key (X-API-KEY header).
    
    Args:
        request: FastAPI request object
        db_session: Database session
        
    Returns:
        user_id string if authenticated
        
    Raises:
        HTTPException: If neither authentication method succeeds
    """
    # Try JWT authentication first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        try:
            supabase_user = await get_current_supabase_user(request)
            logger.info(f"User authenticated via JWT: {supabase_user.id}")
            return supabase_user.id
        except HTTPException as e:
            logger.warning(f"JWT authentication failed: {e.detail}")
            # Continue to try API key authentication
        except Exception as e:
            logger.warning(f"Unexpected error in JWT authentication: {e}")
            # Continue to try API key authentication
    
    # Try API key authentication
    api_key = request.headers.get("X-API-KEY")
    if api_key:
        try:
            user_id = await get_current_user_from_api_key_header(request, db_session)
            if user_id:
                logger.info(f"User authenticated via API key: {user_id}")
                return user_id
        except HTTPException as e:
            logger.warning(f"API key authentication failed: {e.detail}")
        except Exception as e:
            logger.warning(f"Unexpected error in API key authentication: {e}")
    
    # If we get here, both authentication methods failed
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide either 'Authorization: Bearer <jwt_token>' or 'X-API-KEY: <api_key>' header"
    ) 