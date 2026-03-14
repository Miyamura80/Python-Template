"""Subscription configuration loader."""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger as log


class SubscriptionConfig:
    """Load and expose subscription tier limits."""

    def __init__(self) -> None:
        self.config_path = Path(__file__).parent / "subscription_config.yaml"
        self.data: dict[str, Any] = self._load_config()
        self.tier_limits: dict[str, dict[str, int]] = self._load_tier_limits()
        self.default_tier: str | None = self._load_default_tier()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Subscription config not found at {self.config_path.resolve()}"
            )

        with open(self.config_path, "r") as file:
            return yaml.safe_load(file) or {}

    def _load_tier_limits(self) -> dict[str, dict[str, int]]:
        tier_limits = self.data.get("tier_limits", {})
        if not tier_limits:
            log.warning("No tier_limits defined in subscription_config.yaml")
        return tier_limits

    def _load_default_tier(self) -> str | None:
        default_tier = self.data.get("default_tier")
        if default_tier:
            return str(default_tier)
        if self.tier_limits:
            fallback_tier = next(iter(self.tier_limits.keys()))
            log.warning(
                "default_tier not set in subscription_config.yaml; "
                "falling back to first tier key: %s",
                fallback_tier,
            )
            return fallback_tier
        return None

    def limit_for_tier(self, tier_key: str, limit_name: str) -> int | None:
        """Return the configured limit value for a tier and limit name."""
        tier_config = self.tier_limits.get(tier_key)
        if tier_config is None:
            return None
        limit_value = tier_config.get(limit_name)
        return int(limit_value) if limit_value is not None else None


subscription_config = SubscriptionConfig()

__all__ = ["subscription_config", "SubscriptionConfig"]
