import os
import sys
import importlib
from pathlib import Path
from tests.test_template import TestTemplate

root_dir = Path(__file__).parent.parent.parent

class TestProdConfig(TestTemplate):
    def test_prod_config_loading(self):
        # Store original environment
        original_environ = os.environ.copy()

        # --- Test Production Environment ---
        os.environ['DEV_ENV'] = 'prod'
        os.environ['OPENAI_API_KEY'] = 'prod_api_key'
        os.environ['ANTHROPIC_API_KEY'] = 'prod_api_key'
        os.environ['GROQ_API_KEY'] = 'prod_api_key'
        os.environ['PERPLEXITY_API_KEY'] = 'prod_api_key'
        os.environ['GEMINI_API_KEY'] = 'prod_api_key'


        # Reload the common.global_config module to pick up the new .env file
        common_module = sys.modules["common.global_config"]
        importlib.reload(common_module)
        reloaded_config = common_module.global_config

        # Assert that the variables are loaded from .prod.env
        assert reloaded_config.DEV_ENV == "prod", "Should load from .prod.env"
        assert reloaded_config.OPENAI_API_KEY == "prod_api_key", "Should load from .prod.env"

        # Assert that production_config.yaml overrides global_config.yaml
        assert reloaded_config.example_parent.example_child == "prod_value", "Should be overridden by production_config.yaml"

        # --- Test Development Environment ---
        # Restore original environment and set up for dev
        os.environ.clear()
        os.environ.update(original_environ)
        os.environ['DEV_ENV'] = 'dev'
        os.environ['OPENAI_API_KEY'] = 'dev_api_key'
        os.environ['ANTHROPIC_API_KEY'] = 'dev_api_key'
        os.environ['GROQ_API_KEY'] = 'dev_api_key'
        os.environ['PERPLEXITY_API_KEY'] = 'dev_api_key'
        os.environ['GEMINI_API_KEY'] = 'dev_api_key'


        # Reload the common.global_config module again
        importlib.reload(common_module)
        reloaded_config = common_module.global_config

        # Assert that the variables are loaded from .env
        assert reloaded_config.DEV_ENV == "dev", "Should load from .env"
        assert reloaded_config.OPENAI_API_KEY == "dev_api_key", "Should load from .env"

        # Assert that global_config.yaml is used
        assert reloaded_config.example_parent.example_child == "example_value", "Should use value from global_config.yaml"

        # --- Cleanup ---
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_environ)

    def test_prod_env_file_is_loaded_when_in_dot_env(self, monkeypatch):
        # 1. Ensure a clean environment
        if "DEV_ENV" in os.environ:
            monkeypatch.delenv("DEV_ENV")

        dot_env_path = root_dir / ".env"
        prod_dot_env_path = root_dir / ".prod.env"

        try:
            # 2. Create a temporary .env file with DEV_ENV=prod
            dot_env_content = "DEV_ENV=prod\nOPENAI_API_KEY=from_env\n"
            with open(dot_env_path, "w") as f:
                f.write(dot_env_content)

            # 3. Create a temporary .prod.env file
            prod_dot_env_content = "OPENAI_API_KEY=from_prod_env\n"
            with open(prod_dot_env_path, "w") as f:
                f.write(prod_dot_env_content)

            # 4. Set other required env vars to avoid errors
            monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
            monkeypatch.setenv("GROQ_API_KEY", "key")
            monkeypatch.setenv("PERPLEXITY_API_KEY", "key")
            monkeypatch.setenv("GEMINI_API_KEY", "key")

            # 5. Reload the config module
            common_module = sys.modules["common.global_config"]
            importlib.reload(common_module)
            reloaded_config = common_module.global_config

            # 6. Assert that the key is loaded from the .prod.env file
            assert reloaded_config.OPENAI_API_KEY == "from_prod_env"

        finally:
            # 7. Cleanup
            if os.path.exists(dot_env_path):
                os.remove(dot_env_path)
            if os.path.exists(prod_dot_env_path):
                os.remove(prod_dot_env_path)
