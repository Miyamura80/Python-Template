"""
API key authentication helpers.
"""

from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import HTTPException, Request
from loguru import logger as log
from sqlalchemy.orm import Session

from src.db.models.public.api_keys import APIKey
from src.utils.logging_config import setup_logging

# Setup logging at module import
setup_logging()

API_KEY_HEADER = "X-API-KEY"
API_KEY_PREFIX = "sk_"
KEY_PREFIX_LENGTH = 8


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_api_key(api_key: str) -> str:
    """
    Return a deterministic SHA-256 hash for an API key.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key_value() -> str:
    """
    Generate a new API key value with a consistent prefix.
    """
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def create_api_key(
    db_session: Session,
    user_id: str,
    name: str | None = None,
    expires_at: datetime | None = None,
) -> str:
    """
    Create and persist a new API key for the given user.

    Only the hashed value is stored; the raw key is returned once for the caller.
    """
    raw_key = generate_api_key_value()
    key_prefix = raw_key[:KEY_PREFIX_LENGTH]
    key_hash = hash_api_key(raw_key)

    api_key = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        expires_at=expires_at,
    )

    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    log.info(f"Created API key for user {user_id} with prefix {key_prefix}")
    return raw_key


def validate_api_key(api_key: str, db_session: Session) -> APIKey:
    """
    Validate the provided API key and return the associated record.
    """
    key_hash = hash_api_key(api_key)
    api_key_record = (
        db_session.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    )

    if not api_key_record:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if api_key_record.revoked:
        raise HTTPException(status_code=401, detail="API key has been revoked")

    if api_key_record.expires_at and api_key_record.expires_at <= _utcnow():
        raise HTTPException(status_code=401, detail="API key has expired")

    api_key_record.last_used_at = _utcnow()
    try:
        db_session.commit()
    except Exception as exc:
        db_session.rollback()
        log.error(f"Failed to update API key {api_key_record.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update API key metadata")

    return api_key_record


async def get_current_user_from_api_key_header(
    request: Request, db_session: Session
) -> str:
    """
    Extract and validate the API key from the request headers.
    """
    api_key = request.headers.get(API_KEY_HEADER)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-KEY header")

    try:
        api_key_record = validate_api_key(api_key, db_session)
    except HTTPException:
        raise
    except Exception as exc:
        log.error(f"Unexpected error during API key validation: {exc}")
        raise HTTPException(status_code=500, detail="Failed to validate API key")

    log.info(f"User authenticated via API key: {api_key_record.user_id}")
    return str(api_key_record.user_id)
