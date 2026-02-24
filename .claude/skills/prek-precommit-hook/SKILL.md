---
name: prek-precommit-hook
description: Instructions for managing and running git hooks using `prek`. Use this skill for any mention of pre-commit hooks, as `prek` overrides pre-commit hooks.
---
# Prek Pre-commit Hook Skill

This skill provides instructions for using `prek`, a fast, native pre-commit runner that replaces the traditional Python-based `pre-commit`. **`prek` should be used for any mention of pre-commit hooks and overrides traditional pre-commit hooks.**

## Commands

Use the following commands to interact with `prek`:

- `prek run`: Runs the configured hooks on the staged files.
- `prek run --all-files`: Runs the configured hooks on all files in the repository.
- `prek install`: Installs the git hooks into `.git/hooks`.
- `prek uninstall`: Uninstalls the git hooks.
- `prek list`: Lists the configured hooks.

## Configuration

The configuration is stored in `prek.toml` in the root of the repository.

Example `prek.toml`:
```toml
[[repos]]
repo = "https://github.com/pre-commit/pre-commit-hooks"
rev = "v4.6.0"
hooks = [
    { id = "check-added-large-files" },
]

[[repos]]
repo = "local"
hooks = [
    { id = "ruff-check", name = "Run ruff linter", entry = "uv run ruff check", language = "system", pass_filenames = false, always_run = true },
]
```

## Workflow

1.  **Before Committing**: `prek` hooks will run automatically if installed via `prek install`.
2.  **Manual Check**: You can manually run checks using `prek run --all-files`.
3.  **CI**: In CI environments, you can use `prek run --all-files` to enforce checks.
