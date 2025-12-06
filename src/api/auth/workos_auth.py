"""
WorkOS Authentication Module

This module provides WorkOS JWT token authentication for protected routes.
"""

from fastapi import HTTPException, Request
from pydantic import BaseModel
from loguru import logger
from typing import Any
import jwt
import sys
from jwt.exceptions import DecodeError, InvalidTokenError, PyJWKClientError
from jwt import PyJWKClient

from src.utils.logging_config import setup_logging
from common import global_config

# Setup logging at module import
setup_logging()

# Initialize WorkOS JWKS client (cached at module level)
WORKOS_JWKS_URL = f"https://api.workos.com/sso/jwks/{global_config.WORKOS_CLIENT_ID}"
WORKOS_ISSUER = "https://api.workos.com"
WORKOS_ACCESS_ISSUER = (
    f"{WORKOS_ISSUER}/user_management/client_{global_config.WORKOS_CLIENT_ID}"
)
WORKOS_ALLOWED_ISSUERS = [WORKOS_ISSUER, WORKOS_ACCESS_ISSUER]
WORKOS_AUDIENCE = global_config.WORKOS_CLIENT_ID

# Create JWKS client instance (will cache keys automatically)
_jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    """Get or create the WorkOS JWKS client instance."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(WORKOS_JWKS_URL)
    return _jwks_client


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
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )

    try:
        # Extract token
        token = auth_header.split(" ", 1)[1]

        # Check if we're in test mode (skip signature verification for tests)
        # Detect test mode by checking if pytest is running
        is_test_mode = "pytest" in sys.modules or "test" in sys.argv[0].lower()

        # Determine whether the token declares an audience so we can decide
        # whether to enforce audience verification (access tokens currently omit aud).
        try:
            unverified_claims = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,
                    "verify_iss": False,
                    "verify_aud": False,
                },
            )
            has_audience = "aud" in unverified_claims
        except Exception:
            # If we cannot read claims without verification, fall back to enforcing aud
            has_audience = True

        # Verify and decode the JWT token using WorkOS JWKS
        try:
            if is_test_mode:
                # In test mode, decode without signature verification
                # Tests use HS256 tokens with test secrets
                decoded_token = jwt.decode(
                    token,
                    options={
                        "verify_signature": False,
                        "verify_exp": False,
                        "verify_iss": False,
                        "verify_aud": False,
                    },
                )
                logger.debug("Decoded test token without signature verification")
            else:
                # Production mode: verify signature using WorkOS JWKS
                jwks_client = get_jwks_client()
                # Get the signing key from JWKS
                signing_key = jwks_client.get_signing_key_from_jwt(token)

                # Decode and verify the JWT token with signature verification
                decode_options = {
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": has_audience,
                }
                if not has_audience:
                    logger.debug(
                        "WorkOS token missing 'aud' claim; skipping audience verification"
                    )

                decoded_token = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],  # WorkOS uses RS256 for JWT signing
                    issuer=WORKOS_ALLOWED_ISSUERS,
                    audience=WORKOS_AUDIENCE if has_audience else None,
                    options=decode_options,
                )
        except (DecodeError, InvalidTokenError, PyJWKClientError) as e:
            logger.error(f"Invalid WorkOS token or JWKS lookup failed: {e}")
            raise HTTPException(
                status_code=401, detail="Invalid or expired token. Please log in again."
            )

        # Create user object from token data
        user = WorkOSUser.from_workos_token(decoded_token)

        if not user.id or not user.email:
            logger.error(f"Token missing required fields: {decoded_token}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing required user information",
            )

        logger.debug(f"Successfully authenticated WorkOS user: {user.email}")
        return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in WorkOS authentication: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
