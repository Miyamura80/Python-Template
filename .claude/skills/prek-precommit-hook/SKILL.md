---
name: prek-precommit-hook
description: Instructions for using prek (pre-commit replacement). This skill should be used for any mention of pre-commit hooks; prek overrides standard pre-commit hooks.
---
# Prek Skill (prek-precommit-hook)

This skill provides instructions for using `prek` to manage git hooks and run checks.
It should be used for any mention of pre-commit hooks, as `prek` overrides standard pre-commit hooks in this repository.

## Commands

- `prek run`: Run hooks on changed files.
- `prek run --all-files`: Run hooks on all files in the repository.
- `prek install`: Install git hooks to run automatically on commit.
- `prek run <hook_id>`: Run a specific hook by its ID.
- `prek run --help`: Show help and available options.

## Workflow

1. **Setup**: Run `prek install` to set up git hooks.
2. **Pre-commit**: Hooks will run automatically on commit, replacing standard pre-commit behavior.
3. **Manual Check**: Run `prek run --all-files` to check everything manually.
4. **Configuration**: Hooks are configured in `prek.toml`.
