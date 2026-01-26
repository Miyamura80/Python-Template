# Contributing

## Getting Started

1.  **Prerequisites**:
    *   Python >= 3.12
    *   `uv` (for dependency management)

2.  **Setup**:
    ```bash
    make setup
    ```

3.  **Run Tests**:
    ```bash
    make test
    ```

## Development Workflow

1.  Create a new branch for your feature/fix.
2.  Make your changes.
3.  Ensure code quality commands pass:
    ```bash
    make ci
    ```
    This runs formatting, linting, type checking, and dead code detection.

## Code Style

*   Follow the existing conventions (snake_case for functions, CamelCase for classes).
*   Use `ruff` for linting and formatting (handled by `make fmt` and `make ruff`).
*   Add tests for new features.

## Pull Requests

*   Keep PRs focused on a single change.
*   Update documentation if necessary.
