import os
import importlib
import sys
from pathlib import Path

# Get the path to the root directory
root_dir = Path(__file__).parent.parent.parent


def test_env_var_loading_precedence(monkeypatch):
    """
    Test that environment variables are loaded with the correct precedence:
    .env file > system environment variables.
    """
    # 1. Set mock system environment variables
    monkeypatch.setenv("DEV_ENV", "system")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "system_anthropic_key")
    monkeypatch.setenv("GROQ_API_KEY", "system_groq_key")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "system_perplexity_key")
    monkeypatch.setenv("GEMINI_API_KEY", "system_gemini_key")
    # This one is not in the .env file, so it should be loaded from the system env
    monkeypatch.setenv("OPENAI_API_KEY", "system_openai_key")

    # 2. Create a temporary .env file
    dot_env_content = "DEV_ENV=dotenv\n" "OPENAI_API_KEY=dotenv_openai_key\n"
    dot_env_path = root_dir / ".env"
    with open(dot_env_path, "w") as f:
        f.write(dot_env_content)

    # 3. Reload the global_config module to pick up the new .env file
    global_config_module = sys.modules["global_config.global_config"]
    importlib.reload(global_config_module)
    reloaded_config = global_config_module.global_config

    # 4. Assert that the variables are loaded with the correct precedence
    assert reloaded_config.DEV_ENV == "dotenv", "Should load from .env first"
    assert (
        reloaded_config.ANTHROPIC_API_KEY == "system_anthropic_key"
    ), "Should fall back to system env"
    assert (
        reloaded_config.OPENAI_API_KEY == "dotenv_openai_key"
    ), "Should load from .env"

    # Clean up the .env file
    os.remove(dot_env_path)

    # Reload the original config to avoid side effects on other tests
    importlib.reload(global_config_module)
