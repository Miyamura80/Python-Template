# Agent Instructions

This document provides instructions for you, the AI agent, on how to work with this codebase. Please follow these guidelines carefully.

## Before Submitting

1.  **Run Verification Checks:** After major changes, always run the following commands to ensure code quality:
    -   `make fmt` (Format code)
    -   `make ruff` (Lint code)
    -   `make vulture` (Check for dead code)
    If any issues arise, address them.

2.  **Run CI:** After running the above, run `make ci` to ensure all tests and checks pass. This allows you to see CI outputs and fix issues before submitting.

## Environment Setup

Before running the project, you need to set the required environment variables. These are defined in `common/global_config.py`.

Create a `.env` file in the root of the project and add the environment variables defined in `common/global_config.py`. You can find the required keys as fields in the `Config` class (any field with type `str` that looks like an API key).

## Coding Style

-   **Variable Naming:** Use `snake_case` for all function, file, and directory names. Use `CamelCase` for class names. Use `lowercase` for variable names and `ALL_CAPS` for constants.
-   **Indentation:** Use 4 spaces for indentation.
-   **Strings:** Use double quotes for strings.
-   **Documentation:** Don't make markdown docs/references unless explicitly told.

## Global Configuration

This project uses a centralized system for managing global configuration, including hyperparameters and secrets. The configuration is powered by **pydantic-settings**.

**Configuration Files:**
-   `common/global_config.yaml` - Base configuration values
-   `common/config_models.py` - Pydantic models defining the structure and validation
-   `common/global_config.py` - Main Config class using BaseSettings
-   `.env` - Environment variables and secrets (git-ignored)

**Hyperparameters:** Add any hyperparameters that apply across the entire codebase to `common/global_config.yaml`. Do not define them as constants in the code.
**Secrets:** Store private keys in a `.env` file.

```python
from common import global_config

# Access non-secret values
print(global_config.example_parent.example_child)

# Access secret values
print(global_config.OPENAI_API_KEY)
```

## Dependency Management & Running Code

**Dependencies:**
Never use `uv pip`. Instead, run `uv --help` to see available commands.

**Running Code:**
-   **Run a Python file:** `uv run python -m path_to.python_file.python_file_name` (Important: without `.py` extension)
-   **Run Tests:** `uv run pytest path/to/pytest/file.py`

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

-   **Configuration:** Never configure logging directly in your files. The log levels are controlled by `common/global_config.yaml`.

## LLM Inference with DSPY

For all LLM inference tasks, you must use the `DSPYInference` module.

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

Use LangFuse for observability.

-   **Usage:** Use the `@observe` decorator for functions that contain LLM calls. If you need a more descriptive name for the observation span, use `langfuse_context.update_current_observation`.

```python
from langfuse.decorators import observe, langfuse_context

@observe
def function_name(...):
    # To give the span a more descriptive name, update the observation
    langfuse_context.update_current_observation(name=f"some-descriptive-name")
```

## Long-Running Code

For code expected to run for a long time:

-   **Structure:** Break down into `init()`, `continue(id)`, and `cleanup(id)`.
-   **State:** Checkpoint state and resume using an `id`.
-   **System Boundaries:** Implement rate limits, timeouts, retries, and log tracing when calling external services.
-   **Output:** Keep data structured until the end.

## Testing

You are required to write tests for new features.

-   **Framework:** Use `pytest`.
-   **Location:** Add new tests to `tests/`. Ensure `__init__.py` exists in subdirectories.
-   **Structure:** Inherit from `TestTemplate`.

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

**E2E Tests:** For API routes, refer to `tests/e2e/e2e_test_base.py` or `.cursor/rules/routes.mdc` for templates on writing end-to-end tests.

## Type Hinting

-   **Use Built-ins:** Use `list`, `tuple`, `dict` directly instead of importing `List`, `Tuple`, `Dict` from `typing`.

## GitHub Actions

-   **Authentication:** Use `secrets.GITHUB_TOKEN` whenever possible.

## Detailed Guidelines

For specific tasks, please refer to the detailed guidelines in the `.cursor/rules/` directory:

*   **Commit Messages:** See `.cursor/rules/commit_msg.mdc` for the mandatory commit message convention and emoji usage.
*   **API Routes:** When adding or modifying API routes (especially for authentication and adding new endpoints), refer to `.cursor/rules/routes.mdc`.
*   **Deprecations:** Check `.cursor/rules/deprecated.mdc` for information on deprecated modules and patterns (e.g., `datetime.utcnow`).
*   **Railway Deployment:** If dealing with deployment or build artifacts on Railway, consult `.cursor/rules/railway.mdc` regarding file handling (e.g., `.txt` vs `.md` files).
