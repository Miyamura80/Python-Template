"""Shared utilities for agent routes."""

import uuid

from loguru import logger as log

from src.utils.logging_config import setup_logging

setup_logging()


def user_uuid_from_str(user_id: str) -> uuid.UUID:
    """
    Convert user ID string to UUID.

    WorkOS user IDs are not guaranteed to be UUIDs. If parsing fails, fall back
    to a deterministic uuid5 so we can store rows against the UUID-typed FK.
    """
    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        derived_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id))
        log.debug(
            "Generated deterministic UUID from non-UUID user id %s: %s",
            user_id,
            derived_uuid,
        )
        return derived_uuid
