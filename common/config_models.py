"""
Pydantic models for global configuration structure.

This module defines all the nested configuration models used by the Config class.
Each model corresponds to a section in the global_config.yaml file and provides
type validation and structure for the configuration data.
"""

from pydantic import BaseModel, Field


class ExampleParent(BaseModel):
    """Example configuration parent model."""

    example_child: str


class DefaultLlm(BaseModel):
    """Default LLM configuration."""

    default_model: str
    fallback_model: str | None = None
    default_temperature: float
    default_max_tokens: int


class RetryConfig(BaseModel):
    """Retry configuration for LLM requests."""

    max_attempts: int
    min_wait_seconds: int
    max_wait_seconds: int


class LlmConfig(BaseModel):
    """LLM configuration including caching and retry settings."""

    cache_enabled: bool
    retry: RetryConfig


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


class RedactionPattern(BaseModel):
    """Configuration for a specific redaction pattern."""

    name: str
    regex: str
    placeholder: str


class RedactionConfig(BaseModel):
    """Configuration for log redaction/scrubbing."""

    enabled: bool = True
    use_default_pii: bool = True
    patterns: list[RedactionPattern] = []


class LoggingConfig(BaseModel):
    """Complete logging configuration."""

    verbose: bool
    format: LoggingFormatConfig
    levels: LoggingLevelsConfig
    redaction: RedactionConfig = Field(default_factory=lambda: RedactionConfig())


class FeaturesConfig(BaseModel):
    """Feature flags configuration."""

    model_config = {"extra": "allow"}  # Allow arbitrary flags
