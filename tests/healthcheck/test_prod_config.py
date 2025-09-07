import os
import sys
import importlib
from tests.test_template import TestTemplate

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
        import common.global_config
        importlib.reload(common.global_config)
        reloaded_config = common.global_config.global_config

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
        importlib.reload(common.global_config)
        reloaded_config = common.global_config.global_config

        # Assert that the variables are loaded from .env
        assert reloaded_config.DEV_ENV == "dev", "Should load from .env"
        assert reloaded_config.OPENAI_API_KEY == "dev_api_key", "Should load from .env"

        # Assert that global_config.yaml is used
        assert reloaded_config.example_parent.example_child == "example_value", "Should use value from global_config.yaml"

        # --- Cleanup ---
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_environ)
