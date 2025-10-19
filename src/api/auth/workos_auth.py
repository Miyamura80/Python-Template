"""
WorkOS Authentication Module

This module provides WorkOS JWT token authentication for protected routes.
"""

from fastapi import HTTPException, Request
from pydantic import BaseModel
from loguru import logger
from typing import Any
import jwt
from jwt.exceptions import InvalidTokenError

from common import global_config
from src.utils.logging_config import setup_logging

# Setup logging at module import
setup_logging()


class WorkOSUser(BaseModel):
    """WorkOS user model"""
    id: str  # noqa
    email: str  # noqa
    first_name: str | None = None  # noqa
    last_name: str | None = None  # noqa

    @classmethod
    def from_workos_token(cls, token_data: dict[str, Any]):
        """Create WorkOSUser from decoded JWT token data"""
        return cls(
            id=token_data.get("sub", ""),
            email=token_data.get("email", ""),
            first_name=token_data.get("first_name"),
            last_name=token_data.get("last_name"),
        )


async def get_current_workos_user(request: Request) -> WorkOSUser:
    """
    Validate the user's WorkOS JWT token and return the user.

    WorkOS tokens are JWTs that can be verified using the WorkOS client ID.

    Args:
        request: FastAPI request object

    Returns:
        WorkOSUser object with user information

    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    try:
        # Extract token
        token = auth_header.split(" ", 1)[1]

        # Decode and verify the JWT token
        # WorkOS tokens are signed JWTs - we verify without signature for now
        # In production, you should verify the signature using WorkOS public keys
        try:
            decoded_token = jwt.decode(
                token,
                options={"verify_signature": False},  # TODO: Verify signature in production
            )
        except InvalidTokenError as e:
            logger.error(f"Invalid WorkOS token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token. Please log in again."
            )

        # Check if token has expired
        import time
        if "exp" in decoded_token:
            if decoded_token["exp"] < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired. Please log in again."
                )

        # Create user object from token data
        user = WorkOSUser.from_workos_token(decoded_token)

        if not user.id or not user.email:
            logger.error(f"Token missing required fields: {decoded_token}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing required user information"
            )

        logger.debug(f"Successfully authenticated WorkOS user: {user.email}")
        return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in WorkOS authentication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

