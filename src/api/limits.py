"""Tier-aware quota enforcement helpers."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from loguru import logger as log
from sqlalchemy.orm import Session

from common.subscription_config import subscription_config
from src.db.models.public.agent_conversations import AgentConversation, AgentMessage
from src.db.models.stripe.subscription_types import SubscriptionTier
from src.db.models.stripe.user_subscriptions import UserSubscriptions
from src.utils.logging_config import setup_logging

setup_logging()

DEFAULT_LIMIT_NAME = "daily_chat"
DEFAULT_TIER_CONFIG_KEY = "free_tier"


@dataclass
class LimitStatus:
    """Represents the state of a quota check."""

    tier: str
    limit_name: str
    limit_value: int
    used_today: int
    remaining: int
    reset_at: datetime

    @property
    def is_within_limit(self) -> bool:
        return self.used_today < self.limit_value

    def to_error_detail(self) -> dict[str, str | int]:
        """Standardized error payload for limit breaches."""
        readable_limit = self.limit_name.replace("_", " ")
        return {
            "code": "daily_limit_exceeded",
            "tier": self.tier,
            "limit": self.limit_value,
            "used": self.used_today,
            "remaining": self.remaining,
            "limit_name": self.limit_name,
            "reset_at": self.reset_at.isoformat(),
            "message": (
                f"{readable_limit.capitalize()} limit reached. "
                "Upgrade your plan or wait until reset."
            ),
        }


def _start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _normalize_tier_key(raw_tier: str | None) -> str:
    if not raw_tier:
        return subscription_config.default_tier or DEFAULT_TIER_CONFIG_KEY

    normalized = str(raw_tier).lower()
    if normalized in subscription_config.tier_limits:
        return normalized

    suffixed = f"{normalized}_tier"
    if suffixed in subscription_config.tier_limits:
        return suffixed

    unsuffixed = normalized.removesuffix("_tier")
    if unsuffixed in subscription_config.tier_limits:
        return unsuffixed

    log.warning(
        "Unknown subscription tier %s; falling back to default tier %s",
        raw_tier,
        subscription_config.default_tier or DEFAULT_TIER_CONFIG_KEY,
    )
    return subscription_config.default_tier or DEFAULT_TIER_CONFIG_KEY


def _resolve_tier_for_user(db: Session, user_uuid: uuid.UUID) -> str:
    subscription = (
        db.query(UserSubscriptions)
        .filter(UserSubscriptions.user_id == user_uuid)
        .first()
    )
    tier_value = (
        subscription.subscription_tier if subscription else SubscriptionTier.FREE.value
    )
    return _normalize_tier_key(tier_value)


def _resolve_limit_value(tier_key: str, limit_name: str) -> int:
    limit_value = subscription_config.limit_for_tier(tier_key, limit_name)
    if limit_value is None:
        raise RuntimeError(f"Limit '{limit_name}' not configured for tier '{tier_key}'")
    return limit_value


def _count_today_user_messages(db: Session, user_uuid: uuid.UUID) -> int:
    start_of_today = _start_of_today()
    return (
        db.query(AgentMessage)
        .join(AgentConversation, AgentConversation.id == AgentMessage.conversation_id)
        .filter(AgentConversation.user_id == user_uuid)
        .filter(AgentMessage.role == "user")
        .filter(AgentMessage.created_at >= start_of_today)
        .count()
    )


def ensure_daily_limit(
    db: Session, user_uuid: uuid.UUID, limit_name: str = DEFAULT_LIMIT_NAME
) -> LimitStatus:
    """
    Ensure the user is within their daily quota for the specified limit.

    Raises:
        HTTPException: 402 Payment Required when the user exceeds their limit.
    """
    tier_key = _resolve_tier_for_user(db, user_uuid)
    limit_value = _resolve_limit_value(tier_key, limit_name)
    used_today = _count_today_user_messages(db, user_uuid)
    remaining = max(limit_value - used_today, 0)
    start_of_today = _start_of_today()

    status_snapshot = LimitStatus(
        tier=tier_key,
        limit_name=limit_name,
        limit_value=limit_value,
        used_today=used_today,
        remaining=remaining,
        reset_at=start_of_today + timedelta(days=1),
    )

    if not status_snapshot.is_within_limit:
        log.info(
            "User %s exceeded %s limit: used %s of %s (%s tier)",
            user_uuid,
            limit_name,
            used_today,
            limit_value,
            tier_key,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=status_snapshot.to_error_detail(),
        )

    log.debug(
        "User %s within %s limit: %s/%s (%s remaining, tier=%s)",
        user_uuid,
        limit_name,
        used_today,
        limit_value,
        remaining,
        tier_key,
    )
    return status_snapshot


__all__ = ["ensure_daily_limit", "LimitStatus", "DEFAULT_LIMIT_NAME"]
