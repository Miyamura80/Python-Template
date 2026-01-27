---
name: code-quality
description: Instructions for running code quality checks and maintaining standards in the Python-Template project.
---
# Code Quality Skill

This skill provides instructions for running code quality checks and maintaining standards in the Python-Template project.

## Commands

Use the following `make` targets to ensure code quality:

- `make fmt`: Runs the `ruff` formatter and formats JSON files.
- `make ruff`: Runs the `ruff` linter to catch common errors and style issues.
- `make vulture`: Searches for dead code across the project.
- `make ty`: Runs the `ty` type checker to ensure type safety.
- `make ci`: Runs all of the above checks (`ruff`, `vulture`, `import_lint`, `ty`, `docs_lint`, `check_deps`) in sequence.

## Workflow

1. **Before Committing**: Always run `make fmt` and `make ruff`.
2. **Major Changes**: Run `make ci` to ensure no regressions in types or dead code.
3. **Continuous Integration**: These checks are enforced in the CI pipeline. Ensure all pass before opening a PR.
