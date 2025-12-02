import os
import yaml
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import warnings
from loguru import logger
import re

# Get the path to the root directory (one level up from common)
root_dir = Path(__file__).parent.parent

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

OPENAI_O_SERIES_PATTERN = r"o(\d+)(-mini)?"


class DictWrapper:
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)


class Config:
    _env_keys = [
        "DEV_ENV",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "PERPLEXITY_API_KEY",
        "GEMINI_API_KEY",
        "BACKEND_DB_URI",
        "TELEGRAM_BOT_TOKEN",
        "STRIPE_TEST_SECRET_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_TEST_WEBHOOK_SECRET",
        "STRIPE_WEBHOOK_SECRET",
        "TEST_USER_EMAIL",
        "TEST_USER_PASSWORD",
        "WORKOS_API_KEY",
        "WORKOS_CLIENT_ID",
    ]

    def __init__(self):
        def recursive_update(default, override):
            for key, value in override.items():
                if isinstance(value, dict) and isinstance(default.get(key), dict):
                    recursive_update(default[key], value)
                else:
                    default[key] = value
            return default

        with open("common/global_config.yaml", "r") as file:
            config_data = yaml.safe_load(file)

        # Load production config and override if in prod environment
        if os.getenv("DEV_ENV") == "prod":
            prod_config_path = root_dir / "common/production_config.yaml"
            if prod_config_path.exists():
                with open(prod_config_path, "r") as file:
                    prod_config_data = yaml.safe_load(file)
                if prod_config_data:
                    config_data = recursive_update(config_data, prod_config_data)
                    logger.warning(
                        "\033[33m❗️ Overwriting common/global_config.yaml with common/production_config.yaml\033[0m"
                    )

            # Load the local .gitignored custom global config if it exists
        custom_config_path = root_dir / ".global_config.yaml"
        if custom_config_path.exists():
            with open(custom_config_path, "r") as file:
                custom_config_data = yaml.safe_load(file)

            # Only create and show warning if there's custom config data
            if custom_config_data:
                # Update the config_data with custom values
                config_data = recursive_update(config_data, custom_config_data)

                # Warning message
                warning_msg = "\033[33m❗️ Overwriting default common/global_config.yaml with .global_config.yaml\033[0m"
                if config_data["logging"]["verbose"]:
                    warning_msg += f"\033[33mCustom .global_config.yaml values:\n---\n{yaml.dump(custom_config_data, default_flow_style=False)}\033[0m"
                logger.warning(warning_msg)

        for key, value in config_data.items():
            if isinstance(value, dict):
                setattr(self, key, DictWrapper(value))
            else:
                setattr(self, key, value)

        # Assert we found all necessary keys
        for key in self._env_keys:
            if os.environ.get(key) is None:
                raise ValueError(f"Environment variable {key} not found")
            else:
                setattr(self, key, os.environ.get(key))

        # Figure out runtime environment
        self.is_local = os.getenv("GITHUB_ACTIONS") != "true"
        self.running_on = "🖥️  local" if self.is_local else "☁️  CI"

    def __getattr__(self, name):
        raise AttributeError(f"'Config' object has no attribute '{name}'")

    def to_dict(self):
        def unwrap(obj):
            if isinstance(obj, DictWrapper):
                return {k: unwrap(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [unwrap(item) for item in obj]
            else:
                return obj

        return {k: unwrap(v) for k, v in self.__dict__.items()}

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
        """Returns the Helicone link for the model."""
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
            logger.error(f"Helicone link not found for model: {model_name}")
            return ""


# Create a singleton instance
global_config = Config()
