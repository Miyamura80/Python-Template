# PRD: Interactive Onboarding CLI

## Introduction

Replace the current `make init` + `make setup` workflow with an interactive CLI built on `typer` + `rich`. The current onboarding requires users to know which make targets to run, in what order, and with what arguments - a fragile and undiscoverable process. The new CLI guides users through every step of project setup: renaming, dependency installation, environment variable configuration, pre-commit activation, and AI-powered banner/logo generation - all in one cohesive flow, with each step also runnable independently.

## Goals

- Provide a single, discoverable entry point for all project onboarding (`python onboard.py` or `uv run onboard`)
- Eliminate the need for users to know `make init`, `make setup`, `make setup_githooks`, `make banner`, `make logo` separately
- Make env variable configuration interactive and guided (checkbox selection + inline input)
- Support modular execution so any individual step can be run or re-run independently
- Fully replace `make init` and `make setup` targets (remove them from Makefile)

## User Stories

### US-001: Create typer CLI scaffold with step registry
**Description:** As a developer, I need the CLI entry point and subcommand structure so that the full flow and individual steps are both accessible.

**Acceptance Criteria:**
- [ ] New file `onboard.py` at project root
- [ ] Uses `typer` as CLI framework with `rich` for output formatting
- [ ] Running `uv run python onboard.py` with no args starts the full interactive flow
- [ ] Each step is also a typer subcommand: `uv run python onboard.py rename`, `uv run python onboard.py deps`, `uv run python onboard.py env`, `uv run python onboard.py hooks`, `uv run python onboard.py media`
- [ ] `--help` shows all available subcommands with descriptions
- [ ] `typer` and `questionary` added as project dependencies via `uv add`
- [ ] Typecheck/lint passes

### US-002: Project rename step (replaces `make init`)
**Description:** As a user setting up a new project from this template, I want to interactively name and describe my project so that all placeholder references are updated.

**Acceptance Criteria:**
- [ ] Prompts for project name (with validation: kebab-case, no spaces)
- [ ] Prompts for project description (free text)
- [ ] Updates `name` field in `pyproject.toml`
- [ ] Updates `description` field in `pyproject.toml`
- [ ] Updates `# Python-Template` heading in `README.md`
- [ ] Updates tagline/description line in `README.md`
- [ ] Shows a rich summary of what was changed
- [ ] Skips with message if project is already renamed (name != "python-template")
- [ ] Runnable standalone via `uv run python onboard.py rename`
- [ ] Typecheck/lint passes

### US-003: Dependency setup step (replaces `make setup`)
**Description:** As a user, I want dependencies installed automatically so that my environment is ready without manual steps.

**Acceptance Criteria:**
- [ ] Checks if `uv` is installed; if not, prints install instructions and exits with error
- [ ] Creates `.venv` if it doesn't exist (via `uv venv`)
- [ ] Runs `uv sync` to install all dependencies
- [ ] Shows a rich spinner/progress during installation
- [ ] Reports success or failure clearly
- [ ] Runnable standalone via `uv run python onboard.py deps`
- [ ] Typecheck/lint passes

### US-004: Environment variable configuration step
**Description:** As a user, I want to interactively select which API keys and secrets I need, then fill them in, so that my `.env` file is configured correctly without manually editing it.

**Acceptance Criteria:**
- [ ] Reads all keys from `.env.example` as the source of truth
- [ ] If `.env` already exists, loads it and identifies which keys are already set (non-empty)
- [ ] Presents a checkbox list (via `questionary.checkbox`) of all env var keys, grouped by service (e.g. "LLM API Keys", "Supabase", "Stripe", "Observability", "Other")
- [ ] Pre-checks keys that already have values in the existing `.env`
- [ ] User ticks which keys they intend to configure
- [ ] For each ticked key that is empty/missing, prompts the user to enter the value (with `password=True` masking for keys containing "SECRET" or "KEY" or "TOKEN" or "PASSWORD")
- [ ] For each ticked key that already has a value, asks "Keep existing value? (Y/n)" - skips if yes
- [ ] Writes/updates `.env` file preserving any comments from `.env.example`
- [ ] Keys the user did not tick are left commented out (prefixed with `#`) in `.env`
- [ ] Prints summary: N keys configured, M keys skipped
- [ ] Runnable standalone via `uv run python onboard.py env`
- [ ] Typecheck/lint passes

### US-005: Pre-commit hooks activation step
**Description:** As a user, I want to be prompted to activate pre-commit hooks so that code quality checks run automatically on every commit.

**Acceptance Criteria:**
- [ ] Shows what hooks are configured (list from `.pre-commit-config.yaml`) using a rich table or panel
- [ ] Recommends activation with a "(Recommended)" label
- [ ] If user accepts, runs `git config core.hooksPath .githooks` (same as `make setup_githooks`)
- [ ] If user declines, prints a note on how to activate later
- [ ] Reports success or skip clearly
- [ ] Runnable standalone via `uv run python onboard.py hooks`
- [ ] Typecheck/lint passes

### US-006: Banner and logo generation step
**Description:** As a user, I want to describe my project's visual theme and have banner and logo assets generated automatically.

**Acceptance Criteria:**
- [ ] Checks if `GEMINI_API_KEY` is set (from `.env` or environment); if not, warns and offers to skip
- [ ] Prompts user for a theme/style description (e.g. "minimalist Japanese wave art", "cyberpunk neon city")
- [ ] Asks if user wants to generate: (a) banner only, (b) logo only, (c) both, (d) skip
- [ ] Passes the theme description to `init/generate_banner.py` and/or `init/generate_logo.py`
- [ ] The generation scripts are updated to accept title + theme description as parameters (not hardcoded in `__main__`)
- [ ] Shows rich spinner during generation with status updates
- [ ] On completion, prints file paths of generated assets
- [ ] Runnable standalone via `uv run python onboard.py media`
- [ ] Typecheck/lint passes

### US-007: Full onboarding flow (orchestrator)
**Description:** As a user, I want to run the full onboarding in sequence so that I go from a fresh clone to a fully configured project in one command.

**Acceptance Criteria:**
- [ ] Running `uv run python onboard.py` (no subcommand) executes all steps in order: rename → deps → env → hooks → media
- [ ] Shows a rich welcome banner/header at the start (project name, brief description of what will happen)
- [ ] Between each step, shows a progress indicator (e.g. "Step 2/5: Dependencies")
- [ ] Each step can be skipped interactively if the user presses 's' or selects "Skip"
- [ ] At the end, prints a rich summary panel: what was done, what was skipped, and suggested next commands (`make test`, `make ci`, `make all`)
- [ ] Typecheck/lint passes

### US-008: Remove old Makefile targets and update docs
**Description:** As a maintainer, I want the old `make init` and `make setup` targets removed and docs updated so that there's one clear onboarding path.

**Acceptance Criteria:**
- [ ] `make init` target removed from Makefile
- [ ] `make setup` target removed from Makefile
- [ ] `make setup_githooks` target removed from Makefile (absorbed into CLI)
- [ ] New `make onboard` target added that runs `uv run python onboard.py`
- [ ] `CLAUDE.md` updated: replace `make init` / `make setup` references with `make onboard` / CLI subcommands
- [ ] `README.md` updated with new onboarding instructions
- [ ] Any other references to old targets in docs are updated
- [ ] Typecheck/lint passes

## Functional Requirements

- FR-1: The CLI must be implemented using `typer` for command structure and `rich` for terminal output formatting
- FR-2: `questionary` must be used for interactive prompts (checkboxes, confirmations, text input)
- FR-3: Running `uv run python onboard.py` with no arguments must execute the full onboarding flow in order: rename → deps → env → hooks → media
- FR-4: Each step must be independently executable as a subcommand (e.g., `uv run python onboard.py env`)
- FR-5: The rename step must update `pyproject.toml` (name, description) and `README.md` (heading, tagline)
- FR-6: The deps step must check for `uv`, create `.venv` if needed, and run `uv sync`
- FR-7: The env step must read keys from `.env.example`, present grouped checkboxes, prompt for values of selected empty keys, and write `.env`
- FR-8: Sensitive env var values (containing KEY, SECRET, TOKEN, PASSWORD in the name) must be masked during input
- FR-9: The hooks step must display configured hooks and run `git config core.hooksPath .githooks` on confirmation
- FR-10: The media step must accept a theme description and invoke `init/generate_banner.py` and/or `init/generate_logo.py` with that description
- FR-11: `init/generate_banner.py` and `init/generate_logo.py` must be refactored to accept parameters (title, theme) instead of using hardcoded `__main__` values
- FR-12: The full flow must show step progress (e.g., "Step 2/5") and allow skipping individual steps
- FR-13: The CLI must print a summary panel at the end of the full flow showing what was completed and what was skipped
- FR-14: `make init`, `make setup`, and `make setup_githooks` must be removed from the Makefile
- FR-15: A new `make onboard` target must be added that runs `uv run python onboard.py`

## Non-Goals

- No web-based or GUI setup wizard - terminal only
- No remote/cloud configuration (e.g., auto-creating Supabase projects or Stripe accounts)
- No automatic validation of API keys (e.g., making test API calls to verify keys work)
- No CI/CD pipeline modifications - the CLI is for local developer setup only
- No backwards compatibility shim for `make init` / `make setup` - they are fully removed

## Design Considerations

- Use `rich.panel.Panel` for section headers and summaries
- Use `rich.progress.Progress` or `rich.spinner.Spinner` for long-running operations (uv sync, image generation)
- Use `rich.table.Table` to display pre-commit hooks list and env var status
- Use `questionary` (not `rich.prompt`) for checkbox selection and interactive prompts, as it supports multi-select natively
- Group env vars logically based on `.env.example` comments or naming prefixes (OPENAI/ANTHROPIC/GROQ/GEMINI → "LLM Keys", SUPABASE → "Supabase", STRIPE → "Stripe", LANGFUSE → "Observability", etc.)
- Maintain the repo's code style: snake_case, double quotes, 4-space indent

## Technical Considerations

- `typer` and `questionary` must be added as project dependencies (`uv add typer questionary`)
- `rich` is already a transitive dependency of `typer` but can also be added explicitly
- `init/generate_banner.py` and `init/generate_logo.py` need refactoring to expose their generation logic as importable functions with parameters, rather than only working via `__main__` blocks
- The `.env.example` file structure should remain the source of truth for which env vars exist - the CLI should not hardcode key names
- The CLI should work immediately after cloning (before `uv sync`) by having minimal imports at the top level - `typer` will already be available since it's a project dependency and `uv run` handles the venv

## Success Metrics

- A user can go from `git clone` to fully configured project in under 3 minutes (excluding image generation time)
- Zero knowledge of Makefile targets required - `make onboard` or `uv run python onboard.py` is the only command a new user needs to know
- Each individual step is re-runnable without side effects (idempotent)
- All existing CI checks pass after onboarding (`make ci`)

## Open Questions

- Should the CLI detect if it's being run inside an existing project (already renamed) and default to re-running only the deps/env steps?
- Should we add a `--non-interactive` flag that accepts all defaults for CI/scripting use cases?
- Should env var grouping be derived from comments in `.env.example` (requires a comment convention) or hardcoded in the CLI?
