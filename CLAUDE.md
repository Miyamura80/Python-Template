# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Super-opinionated Python stack for fast development. Python >= 3.12 required. Uses `uv` for dependency management (not pip).

## Common Commands

```bash
# Setup & Run
make init name=... description=... # Initialize project name and description
make setup          # Create/update .venv and sync dependencies
make all            # Run main.py with setup

# Testing
make test           # Run pytest on tests/
make test_fast      # Run fast tests (no slow/nondeterministic)
make test_flaky     # Repeat fast tests to detect flakiness
make test_slow      # Run slow tests only
make test_nondeterministic # Run nondeterministic tests only

# Code Quality (run after major changes)
make fmt            # Run ruff formatter + JSON formatting
make ruff           # Run ruff linter
make vulture        # Find dead code
make ty             # Run type checker
make lint_links     # Check for broken links in markdown files (README, etc.)
make ci             # Run all CI checks (ruff, vulture, ty, import_lint, docs_lint, check_deps, lint_links)

# Dependencies
uv sync             # Install dependencies (not pip install)
uv add <pkg>        # Add new dependency
uv run python <file> # Run Python files
uv run pytest path/to/test.py  # Run specific test

# Release
# 1. Update version in pyproject.toml
# 2. Tag the commit: git tag -a v0.1.0 -m "Release v0.1.0"
# 3. Push the tag: git push origin v0.1.0 (triggers Release workflow)
```

## Architecture

- **common/** - Global configuration via pydantic-settings
  - `global_config.yaml` - Base hyperparameters and config values
  - `<name>.yaml` - Optional split configs (loaded as root key `<name>`)
  - `global_config.py` - Config class (access via `from common import global_config`)
  - `.env` - Secrets/API keys (git-ignored)
- **src/** - Source code (utils/)
- **utils/llm/** - LLM inference with DSPY (`dspy_inference.py`) and LangFuse observability
- **tests/** - pytest tests inheriting from `TestTemplate` in `test_template.py`
- **init/** - Initialization scripts (banner generation)

## Code Style

- snake_case for functions/files/directories
- CamelCase for classes
- UPPERCASE for constants
- 4-space indentation, double quotes
- Use built-in types (list, dict, tuple) not typing.List/Dict/Tuple

## Configuration Pattern

```python
from common import global_config

# Access config values
global_config.example_parent.example_child
global_config.llm_config.default_model

# Access secrets from .env
global_config.OPENAI_API_KEY
```

## LLM Inference Pattern

```python
from utils.llm.dspy_inference import DSPYInference
import dspy

class MySignature(dspy.Signature):
    input_field: str = dspy.InputField()
    output_field: str = dspy.OutputField()

inf_module = DSPYInference(pred_signature=MySignature, observe=True)
result = await inf_module.run(input_field="value")
```

## Testing Pattern

```python
from tests.test_template import TestTemplate
from tests.conftest import slow_test, nondeterministic_test

class TestMyFeature(TestTemplate):
    def test_something(self):
        assert self.config is not None

    @slow_test
    def test_slow_operation(self):
        pass
```

## Logging

```python
from loguru import logger as log
from src.utils.logging_config import setup_logging

setup_logging()
log.debug("detailed diagnostic information")
log.info("general informational message")
log.warning("warning message for potentially harmful situations")
log.error("error message for error events")
```

## Commit Message Convention

Use emoji prefixes indicating change type and magnitude (multiple emojis = 5+ files):
- 🏗️ initial implementation
- 🔨 feature changes
- 🐛 bugfix
- ✨ formatting/linting only
- ✅ feature complete with E2E tests
- ⚙️ config changes
- 💽 DB schema/migrations

## Long-Running Code Pattern

Structure as: `init()` → `continue(id)` → `cleanup(id)`
- Keep state serializable
- Use descriptive IDs (runId, taskId)
- Handle rate limits, timeouts, retries at system boundaries

## Git Workflow
- **Protected Branch**: `main` is protected. Do not push directly to `main`. Use PRs.
- **Merge Strategy**: Squash and merge.

## Deprecated

- Don't use `datetime.utcnow()` - use `datetime.now(timezone.utc)`
