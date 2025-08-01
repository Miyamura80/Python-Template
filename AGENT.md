# Agent Instructions

This document provides instructions for you, the AI agent, on how to work with this codebase. Please follow these guidelines carefully.

## Coding Style

-   **Variable Naming:** Use `snake_case` for all function, file, and directory names. Use `CamelCase` for class names. Use `lowercase` for variable names and `ALL_CAPS` for constants.
-   **Indentation:** Use 4 spaces for indentation.
-   **Strings:** Use double quotes for strings.

## Global Configuration

This project uses a centralized system for managing global configuration, including hyperparameters and secrets.

-   **Hyperparameters:** Add any hyperparameters that apply across the entire codebase to `global_config/global_config.yaml`. Do not define them as constants in the code. Examples include `MAX_RETRIES` and `MODEL_NAME`.
-   **Secrets:** Store private keys and other secrets in a `.env` file in the root of the project. These will be loaded automatically. Examples include `OPENAI_API_KEY` and `GITHUB_PERSONAL_ACCESS_TOKEN`. To autoload environment variables, add their names to the `_ENV` class member in `global_config/global_config.py`.

You can access configuration values in your Python code like this:

```python
from global_config import global_config

# Access non-secret values
print(global_config.example_parent.example_child)

# Access secret values
print(global_config.OPENAI_API_KEY)
```

## Logging

This project uses a centralized logging configuration with `loguru`.

-   **Setup:** Always import and call the setup function from `src/utils/logging_config.py` at the beginning of your file.
-   **Usage:** Use the imported `log` object to log messages.

```python
from loguru import logger as log
from src/utils/logging_config import setup_logging

# Set up logging at the start of your file
setup_logging()

# Use the logger as needed
log.info("This is an info message.")
log.error("This is an error message.")
log.debug("This is a debug message.")
```

-   **Configuration:** Never configure logging directly in your files. The log levels are controlled by `global_config/global_config.yaml`.

## LLM Inference with DSPY

For all LLM inference tasks, you must use the `DSPYInference` module. This module handles both standard inference and tool-use and is integrated with our observability tools.

```python
from utils.llm.dspy_inference import DSPYInference
import dspy
import asyncio

class ExtractInfo(dspy.Signature):
    """Extract structured information from text."""
    text: str = dspy.InputField()
    title: str = dspy.OutputField()
    headings: list[str] = dspy.OutputField()
    entities: list[dict[str, str]] = dspy.OutputField(desc="a list of entities and their metadata")

def web_search_tool(query: str) -> str:
    """Search the web for information."""
    return "example search term"

# Inference without tool-use
inf_module = DSPYInference(pred_signature=ExtractInfo)

# Inference with tool-use
inf_module_with_tool_use = DSPYInference(
    pred_signature=ExtractInfo,
    tools=[web_search_tool],
)

result = asyncio.run(inf_module.run(
    text="Apple Inc. announced its latest iPhone 14 today. The CEO, Tim Cook, highlighted its new features in a press release."
))

print(result.title)
print(result.headings)
print(result.entities)
```

## LLM Observability with LangFuse

To ensure we can monitor the behavior of our LLMs, you must use LangFuse for observability.

-   **Usage:** Use the `@observe` decorator for functions that contain LLM calls. If you need a more descriptive name for the observation span, use `langfuse_context.update_current_observation`.

```python
from langfuse.decorators import observe, langfuse_context

@observe
def function_name(...):
    # To give the span a more descriptive name, update the observation
    langfuse_context.update_current_observation(name=f"some-descriptive-name")
```

## Long-Running Code

For any code that is expected to run for a long time, you must follow this pattern to ensure it is resumable, reproducible, and parallelizable.

-   **Structure:** Break down long-running processes into `init()`, `continue(id)`, and `cleanup(id)` functions.
-   **State:** Always checkpoint the state and resume using an `id`. Do not pass any other parameters. This forces the state to be serializable. Use descriptive names for the id, like `runId` or `taskId`.
-   **System Boundaries:** When calling external services (like microservices or LLM APIs), you must implement rate limiting, timeouts, retries, and log tracing.
-   **Output Formatting:** Keep data in a structured format until the very end of the process. Do not format output (e.g., with f-strings) until it is ready to be presented to the user.

## Testing

You are required to write tests for new features.

-   **Framework:** Use `pytest` for all tests.
-   **Location:** Add new tests to the `tests/` directory. If you create a new subdirectory, make sure to add a `__init__.py` file to it.
-   **Structure:** Inherit from `TestTemplate` for all test classes. Use `self.config` for test-specific configuration.

```python
import pytest
from tests.test_template import TestTemplate, slow_test, nondeterministic_test

class TestMyFeature(TestTemplate):
    @pytest.fixture(autouse=True)
    def setup_shared_variables(self, setup):
        # Initialize any shared attributes here
        pass

    # Use decorators for slow or nondeterministic tests
    @slow_test
    def test_my_function(self):
        # Your test code here
        assert True
```

-   **Decorators:** Use the `@slow_test` or `@nondeterministic_test` decorators for tests that are slow or have variable outcomes.
-   **No `unittest`:** Do not use the `unittest` framework.

## Type Hinting

-   **Use Built-ins:** For type hinting, use the built-in collection types (e.g., `list`, `tuple`, `dict`) directly instead of importing `List`, `Tuple`, and `Dict` from the `typing` module. This is standard for Python 3.9 and later.

## GitHub Actions

-   **Authentication:** When writing GitHub Actions workflows, use the built-in `secrets.GITHUB_TOKEN` for authentication whenever possible. This token is automatically generated for each workflow run and has its permissions scoped to the repository. Only use a personal access token (PAT) if you require special privileges that the default token does not provide.
