"""
Pydantic models for global configuration structure.
This module defines all the nested configuration models used by the Config class.
Each model corresponds to a section in the global_config.yaml file and provides
type validation and structure for the configuration data.
"""

from pydantic import BaseModel


class ExampleParent(BaseModel):
    """Example configuration parent model."""

    example_child: str


class DefaultLlm(BaseModel):
    """Default LLM configuration."""

    default_model: str
    fast_model: str
    cheap_model: str
    default_temperature: float
    default_max_tokens: int


class RetryConfig(BaseModel):
    """Retry configuration for LLM requests."""

    max_attempts: int
    min_wait_seconds: int
    max_wait_seconds: int


class TimeoutConfig(BaseModel):
    """Timeout configuration for LLM API requests."""

    api_timeout_seconds: int
    connect_timeout_seconds: int


class LlmConfig(BaseModel):
    """LLM configuration including caching and retry settings."""

    cache_enabled: bool
    retry: RetryConfig
    timeout: TimeoutConfig


class LoggingLocationConfig(BaseModel):
    """Location information display configuration for logging."""

    enabled: bool
    show_file: bool
    show_function: bool
    show_line: bool
    show_for_info: bool
    show_for_debug: bool
    show_for_warning: bool
    show_for_error: bool


class LoggingFormatConfig(BaseModel):
    """Logging format configuration."""

    show_time: bool
    show_session_id: bool
    location: LoggingLocationConfig


class LoggingLevelsConfig(BaseModel):
    """Logging level configuration."""

    debug: bool
    info: bool
    warning: bool
    error: bool
    critical: bool


class LoggingConfig(BaseModel):
    """Complete logging configuration."""

    verbose: bool
    format: LoggingFormatConfig
    levels: LoggingLevelsConfig


class StreamingConfig(BaseModel):
    """Streaming configuration for agent chat."""

    heartbeat_interval_seconds: int
    first_token_timeout_seconds: int
    max_streaming_duration_seconds: int


class AgentChatConfig(BaseModel):
    """Agent chat configuration."""

    history_message_limit: int
    streaming: StreamingConfig


class StripePriceIdsConfig(BaseModel):
    """Stripe price IDs configuration."""

    test: str
    prod: str


class SubscriptionStripeConfig(BaseModel):
    """Subscription Stripe configuration."""

    price_ids: StripePriceIdsConfig


class MeteredConfig(BaseModel):
    """Metered billing configuration."""

    included_units: int
    overage_unit_amount: int
    unit_label: str


class PaymentRetryConfig(BaseModel):
    """Payment retry configuration."""

    max_attempts: int


class SubscriptionConfig(BaseModel):
    """Subscription configuration."""

    stripe: SubscriptionStripeConfig
    metered: MeteredConfig
    trial_period_days: int
    payment_retry: PaymentRetryConfig


class StripeWebhookConfig(BaseModel):
    """Stripe webhook configuration."""

    url: str


class StripeConfig(BaseModel):
    """Stripe configuration."""

    api_version: str
    webhook: StripeWebhookConfig


class TelegramChatIdsConfig(BaseModel):
    """Telegram chat IDs configuration."""

    admin_alerts: str
    test: str


class TelegramConfig(BaseModel):
    """Telegram configuration."""

    chat_ids: TelegramChatIdsConfig


class ServerConfig(BaseModel):
    """Server configuration."""

    allowed_origins: list[str]
