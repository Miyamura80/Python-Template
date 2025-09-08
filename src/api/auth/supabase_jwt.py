from fastapi import HTTPException, Request
from pydantic import BaseModel
import httpx
from global_config import global_config
from loguru import logger
from typing import Any


class SupabaseUser(BaseModel):
    id: str  # noqa
    email: str  # noqa

    @classmethod
    def from_supabase_user(cls, user_data: dict[str, Any]):
        return cls(
            id=user_data.get("id") or user_data.get("sub") or "",
            email=user_data.get("email", ""),
        )


async def get_current_supabase_user(request: Request) -> SupabaseUser:
    """Validate the user's JWT token and return the user"""
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        # Extract token
        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")

        token = auth_header[7:]  # Remove "bearer " prefix

        # Verify token directly with Supabase Auth API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{global_config.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": global_config.SUPABASE_ANON_KEY,
                },
            )

            if response.status_code != 200:
                response_data: dict[str, Any] = {}
                try:
                    response_data = response.json()
                except Exception:
                    pass

                error_code = response_data.get("error_code", "")
                _error_msg = response_data.get("msg", "Invalid token")

                logger.error(
                    f"Authentication failed: Supabase auth returned {response.status_code} - {response.text}"
                )

                # Handle specific error cases
                if response.status_code == 403 and error_code == "session_not_found":
                    raise HTTPException(
                        status_code=401, detail="Session expired. Please log in again."
                    )
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication token is invalid or expired. Please log in again.",
                    )
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication failed. Please log in again.",
                    )

            user_data = response.json()

            # Create simple user object without profile management
            user = SupabaseUser.from_supabase_user(user_data)

            return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except httpx.HTTPError:
        logger.exception("HTTP error when contacting Supabase for authentication")
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        )
    except Exception:
        logger.exception("Unexpected error in authentication")
        raise HTTPException(status_code=500, detail="Internal server error")