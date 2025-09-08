from __future__ import annotations

import base64
import json
from typing import Any

from loguru import logger as log
from src.utils.logging_config import setup_logging
from common import global_config


# Initialize logging for this module
setup_logging()


def extract_bearer_token(authorization_header: str | None) -> str:
    """
    Extract a bearer token from an Authorization header.

    Args:
        authorization_header: The value of the Authorization header.

    Returns:
        The token string.

    Raises:
        ValueError: If the header is missing or not in the expected format.
    """
    if not authorization_header:
        raise ValueError("Missing authorization header")

    prefix = "bearer "
    header_lower = authorization_header.lower()
    if not header_lower.startswith(prefix):
        raise ValueError("Invalid authorization format")

    return authorization_header[len(prefix) :]


def build_supabase_auth_headers(token: str) -> dict[str, str]:
    """
    Build headers for authenticating requests against Supabase Auth endpoints.

    Args:
        token: The JWT access token.

    Returns:
        A dictionary of HTTP headers including Authorization and apikey.
    """
    return {
        "Authorization": f"Bearer {token}",
        "apikey": global_config.SUPABASE_ANON_KEY,
    }


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """
    Decode a JWT without verifying the signature to obtain the payload.

    This performs manual base64url decoding to avoid bringing in heavy deps
    and to match the behavior used in tests.

    Args:
        token: The JWT string.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        ValueError: If the token cannot be decoded.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT structure")

        payload = parts[1]
        # Base64url padding fix
        padding_needed = (4 - len(payload) % 4) % 4
        payload += "=" * padding_needed
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded = json.loads(decoded_bytes.decode("utf-8"))
        return decoded
    except Exception as exc:
        log.error(f"Failed to decode JWT payload: {exc}")
        raise ValueError(f"Failed to decode JWT payload: {exc}")


