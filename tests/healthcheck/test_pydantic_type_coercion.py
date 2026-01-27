"""
Test pydantic-settings automatic type coercion.
This ensures that environment variables (which are always strings) are properly
converted to the correct Python types as defined in the config models.
"""

import importlib
import sys


def test_pydantic_type_coercion(monkeypatch):
    """
    Test that pydantic-settings automatically coerces environment variable strings
    to the correct types (int, float, bool) as defined in the Pydantic models.
    """
    common_module = sys.modules["common.global_config"]

    # Set environment variables with intentionally "wrong" types (but coercible)
    # These should all be automatically converted to the correct types by pydantic-settings

    # Integer coercion tests
    monkeypatch.setenv("DEFAULT_LLM__DEFAULT_MAX_TOKENS", "50000")  # String -> int
    monkeypatch.setenv("LLM_CONFIG__RETRY__MAX_ATTEMPTS", "5")  # String -> int
    monkeypatch.setenv("LLM_CONFIG__RETRY__MIN_WAIT_SECONDS", "2")  # String -> int
    monkeypatch.setenv("LLM_CONFIG__RETRY__MAX_WAIT_SECONDS", "10")  # String -> int

    # Float coercion test
    monkeypatch.setenv("DEFAULT_LLM__DEFAULT_TEMPERATURE", "0.7")  # String -> float

    # Boolean coercion tests
    monkeypatch.setenv("LLM_CONFIG__CACHE_ENABLED", "true")  # String -> bool
    monkeypatch.setenv("LOGGING__VERBOSE", "false")  # String -> bool
    monkeypatch.setenv("LOGGING__FORMAT__SHOW_TIME", "1")  # String '1' -> bool True
    monkeypatch.setenv("LOGGING__LEVELS__DEBUG", "true")  # String -> bool
    monkeypatch.setenv("LOGGING__LEVELS__INFO", "0")  # String '0' -> bool False

    # Reload the config module to pick up the new environment variables
    importlib.reload(common_module)
    config = common_module.global_config

    # Verify integer coercion
    assert isinstance(config.default_llm.default_max_tokens, int), (
        "default_max_tokens should be int"
    )
    assert config.default_llm.default_max_tokens == 50000, (
        "default_max_tokens should be 50000"
    )

    assert isinstance(config.llm_config.retry.max_attempts, int), (
        "max_attempts should be int"
    )
    assert config.llm_config.retry.max_attempts == 5, "max_attempts should be 5"

    assert isinstance(config.llm_config.retry.min_wait_seconds, int), (
        "min_wait_seconds should be int"
    )
    assert config.llm_config.retry.min_wait_seconds == 2, "min_wait_seconds should be 2"

    assert isinstance(config.llm_config.retry.max_wait_seconds, int), (
        "max_wait_seconds should be int"
    )
    assert config.llm_config.retry.max_wait_seconds == 10, (
        "max_wait_seconds should be 10"
    )

    # Verify float coercion
    assert isinstance(config.default_llm.default_temperature, float), (
        "default_temperature should be float"
    )
    assert config.default_llm.default_temperature == 0.7, (
        "default_temperature should be 0.7"
    )

    # Verify boolean coercion
    assert isinstance(config.llm_config.cache_enabled, bool), (
        "cache_enabled should be bool"
    )
    assert config.llm_config.cache_enabled is True, "cache_enabled should be True"

    assert isinstance(config.logging.verbose, bool), "verbose should be bool"
    assert config.logging.verbose is False, "verbose should be False"

    assert isinstance(config.logging.format.show_time, bool), "show_time should be bool"
    assert config.logging.format.show_time is True, (
        "show_time should be True (from '1')"
    )

    assert isinstance(config.logging.levels.debug, bool), "debug should be bool"
    assert config.logging.levels.debug is True, "debug should be True"

    assert isinstance(config.logging.levels.info, bool), "info should be bool"
    assert config.logging.levels.info is False, "info should be False (from '0')"

    # Reload the original config to avoid side effects on other tests
    importlib.reload(common_module)
