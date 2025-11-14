import os
import re
import warnings
import yaml
from pathlib import Path
from typing import Any

from dotenv import load_dotenv, dotenv_values
from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

# Import configuration models
from .config_models import (
    ExampleParent,
    DefaultLlm,
    LlmConfig,
    LoggingConfig,
)

# Get the path to the root directory (one level up from common)
root_dir = Path(__file__).parent.parent

OPENAI_O_SERIES_PATTERN = r"o(\d+)(-mini)?"


# Custom YAML settings source
class YamlSettingsSource(PydanticBaseSettingsSource):
    """
    Custom settings source that loads from YAML files with priority:
    1. .global_config.yaml (highest priority, git-ignored)
    2. production_config.yaml (if DEV_ENV=prod)
    3. global_config.yaml (base config)
    """

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self.yaml_data = self._load_yaml_files()

    def _load_yaml_files(self) -> dict[str, Any]:
        """Load and merge YAML configuration files."""

        def recursive_update(default: dict, override: dict) -> dict:
            """Recursively update nested dictionaries."""
            for key, value in override.items():
                if isinstance(value, dict) and isinstance(default.get(key), dict):
                    recursive_update(default[key], value)
                else:
                    default[key] = value
            return default

        # Load base config
        config_path = root_dir / "common" / "global_config.yaml"
        try:
            with open(config_path, "r") as file:
                config_data = yaml.safe_load(file) or {}
        except FileNotFoundError:
            raise RuntimeError(f"Required config file not found: {config_path}")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Invalid YAML in {config_path}: {e}")

        # Load production config if in prod environment
        if os.getenv("DEV_ENV") == "prod":
            prod_config_path = root_dir / "common" / "production_config.yaml"
            if prod_config_path.exists():
                try:
                    with open(prod_config_path, "r") as file:
                        prod_config_data = yaml.safe_load(file)
                    if prod_config_data:
                        config_data = recursive_update(config_data, prod_config_data)
                        logger.warning(
                            "\033[33m❗️ Overwriting common/global_config.yaml with common/production_config.yaml\033[0m"
                        )
                except FileNotFoundError:
                    logger.warning(
                        f"Production config file not found: {prod_config_path}"
                    )
                except yaml.YAMLError as e:
                    raise RuntimeError(f"Invalid YAML in {prod_config_path}: {e}")

        # Load custom local config if it exists (highest priority)
        custom_config_path = root_dir / ".global_config.yaml"
        if custom_config_path.exists():
            try:
                with open(custom_config_path, "r") as file:
                    custom_config_data = yaml.safe_load(file)

                if custom_config_data:
                    config_data = recursive_update(config_data, custom_config_data)
                    warning_msg = "\033[33m❗️ Overwriting default common/global_config.yaml with .global_config.yaml\033[0m"
                    if config_data.get("logging", {}).get("verbose"):
                        warning_msg += f"\033[33mCustom .global_config.yaml values:\n---\n{yaml.dump(custom_config_data, default_flow_style=False)}\033[0m"
                    logger.warning(warning_msg)
            except FileNotFoundError:
                logger.warning(f"Custom config file not found: {custom_config_path}")
            except yaml.YAMLError as e:
                raise RuntimeError(f"Invalid YAML in {custom_config_path}: {e}")

        return config_data

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """Get field value from YAML data."""
        field_value = self.yaml_data.get(field_name)
        return field_value, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return the complete YAML configuration."""
        return self.yaml_data


class Config(BaseSettings):
    """
    Global configuration using Pydantic Settings.
    Loads from:
    1. Environment variables (from .env or .prod.env)
    2. YAML files (global_config.yaml, production_config.yaml, .global_config.yaml)
    """

    model_config = SettingsConfigDict(
        # Load from .env file (will be handled separately for .prod.env)
        env_file=str(root_dir / ".env"),
        env_file_encoding="utf-8",
        # Allow nested env vars with double underscore
        env_nested_delimiter="__",
        # Case sensitive for field names
        case_sensitive=False,
        # Allow extra fields from YAML
        extra="allow",
    )

    # Top-level fields
    model_name: str
    dot_global_config_health_check: bool
    example_parent: ExampleParent
    default_llm: DefaultLlm
    llm_config: LlmConfig
    logging: LoggingConfig

    # Environment variables (required)
    DEV_ENV: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    GROQ_API_KEY: str
    PERPLEXITY_API_KEY: str
    GEMINI_API_KEY: str

    # Runtime environment (computed)
    is_local: bool = Field(default=False)
    running_on: str = Field(default="")

    @field_validator("is_local", mode="before")
    @classmethod
    def set_is_local(cls, v: Any) -> bool:
        """Set is_local based on GITHUB_ACTIONS env var."""
        return os.getenv("GITHUB_ACTIONS") != "true"

    @field_validator("running_on", mode="before")
    @classmethod
    def set_running_on(cls, v: Any) -> str:
        """Set running_on based on is_local."""
        is_local = os.getenv("GITHUB_ACTIONS") != "true"
        return "🖥️  local" if is_local else "☁️  CI"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the priority order of settings sources.
        Priority (highest to lowest):
        1. Environment variables
        2. .env file
        3. YAML files (custom .global_config.yaml > production_config.yaml > global_config.yaml)
        4. Init settings (passed to constructor)
        """
        return (
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
            init_settings,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()

    def llm_api_key(self, model_name: str | None = None) -> str:
        """Returns the appropriate API key based on the model name."""
        model_identifier = model_name or self.model_name
        if "gpt" in model_identifier.lower() or re.match(
            OPENAI_O_SERIES_PATTERN, model_identifier.lower()
        ):
            return self.OPENAI_API_KEY
        elif (
            "claude" in model_identifier.lower()
            or "anthropic" in model_identifier.lower()
        ):
            return self.ANTHROPIC_API_KEY
        elif "groq" in model_identifier.lower():
            return self.GROQ_API_KEY
        elif "perplexity" in model_identifier.lower():
            return self.PERPLEXITY_API_KEY
        elif "gemini" in model_identifier.lower():
            return self.GEMINI_API_KEY
        else:
            raise ValueError(f"No API key configured for model: {model_identifier}")

    def api_base(self, model_name: str) -> str:
        """Returns the Helicone link for the model.

        Raises:
            ValueError: If no API base is configured for the given model.
        """
        if "gpt" in model_name.lower() or re.match(
            OPENAI_O_SERIES_PATTERN, model_name.lower()
        ):
            return "https://oai.hconeai.com/v1"
        elif "groq" in model_name.lower():
            return "https://groq.helicone.ai/openai/v1"
        elif "perplexity" in model_name.lower():
            return "https://perplexity.helicone.ai"
        elif "gemini" in model_name.lower():
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            raise ValueError(f"No API base configured for model: {model_name}")


# Load .env files before creating the config instance
# Load .env file first, to get DEV_ENV if it's defined there
load_dotenv(dotenv_path=root_dir / ".env", override=True)

# Now, check DEV_ENV and load .prod.env if it's 'prod', overriding .env
if os.getenv("DEV_ENV") == "prod":
    load_dotenv(dotenv_path=root_dir / ".prod.env", override=True)

# Check if .env file has been properly loaded
is_local = os.getenv("GITHUB_ACTIONS") != "true"
if is_local:
    env_file_to_check = ".prod.env" if os.getenv("DEV_ENV") == "prod" else ".env"
    env_values = dotenv_values(root_dir / env_file_to_check)
    if not env_values:
        warnings.warn(f"{env_file_to_check} file not found or empty", UserWarning)

# Create a singleton instance
global_config = Config()
