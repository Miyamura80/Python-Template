# ANSI color codes
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
BLUE=\033[0;34m
RESET=\033[0m

PYTHON=uv run
TEST=uv run pytest
PROJECT_ROOT=.

.DEFAULT_GOAL := help

########################################################
# Help
########################################################

### Help
.PHONY: help docs
help: ## Show this help message
	@echo "$(BLUE)Available Make Targets$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "; category=""} \
		/^### / {category = substr($$0, 5); next} \
		/^[a-zA-Z_-]+:.*?## / { \
			if (category != last_category) { \
				if (last_category != "") print ""; \
				print "$(GREEN)" category ":$(RESET)"; \
				last_category = category; \
			} \
			printf "  $(YELLOW)%-23s$(RESET) %s\n", $$1, $$2 \
		}' $(MAKEFILE_LIST)

########################################################
# Initialization: Delete later
########################################################

### Initialization
banner: check_uv ## Generate project banner image
	@echo "$(YELLOW)🔍Generating banner...$(RESET)"
	@uv run python -m init.generate_banner
	@echo "$(GREEN)✅Banner generated.$(RESET)"

logo: check_uv ## Generate logo and favicon for docs
	@echo "$(YELLOW)🔍Generating logo and favicon...$(RESET)"
	@uv run python -m init.generate_logo
	@echo "$(GREEN)✅Logo and favicon generated in docs/public/$(RESET)"


########################################################
# Check dependencies
########################################################

check_uv:
	@echo "$(YELLOW)🔍Checking uv version...$(RESET)"
	@if ! command -v uv > /dev/null 2>&1; then \
		echo "$(RED)uv is not installed. Please install uv before proceeding.$(RESET)"; \
		exit 1; \
	else \
		uv --version; \
	fi

check_jq:
	@echo "$(YELLOW)🔍Checking jq version...$(RESET)"
	@if ! command -v jq > /dev/null 2>&1; then \
		echo "$(RED)jq is not installed. Please install jq before proceeding.$(RESET)"; \
		echo "$(RED)brew install jq$(RESET)"; \
		exit 1; \
	else \
		jq --version; \
	fi

########################################################
# Setup githooks for linting
########################################################
setup_githooks:
	@echo "$(YELLOW)🔨Setting up githooks on post-commit...$(RESET)"
	chmod +x .githooks/post-commit
	git config core.hooksPath .githooks


########################################################
# Python dependency-related
########################################################

### Setup & Dependencies
setup: check_uv ## Create venv and sync dependencies
	@echo "$(YELLOW)🔎Looking for .venv...$(RESET)"
	@if [ ! -d ".venv" ]; then \
		echo "$(YELLOW)VS Code is not detected. Creating a new one...$(RESET)"; \
		uv venv; \
	else \
		echo "$(GREEN)✅.venv is detected.$(RESET)"; \
	fi
	@echo "$(YELLOW)🔄Updating python dependencies...$(RESET)"
	@uv sync

view_python_venv_size:
	@echo "$(YELLOW)🔍Checking python venv size...$(RESET)"
	@PYTHON_VERSION=$$(cat .python-version | cut -d. -f1,2) && \
	cd .venv/lib/python$$PYTHON_VERSION/site-packages && du -sh . && cd ../../../
	@echo "$(GREEN)Python venv size check completed.$(RESET)"

view_python_venv_size_by_libraries:
	@echo "$(YELLOW)🔍Checking python venv size by libraries...$(RESET)"
	@PYTHON_VERSION=$$(cat .python-version | cut -d. -f1,2) && \
	cd .venv/lib/python$$PYTHON_VERSION/site-packages && du -sh * | sort -h && cd ../../../
	@echo "$(GREEN)Python venv size by libraries check completed.$(RESET)"

########################################################
# Run Main Application
########################################################

### Running
all: setup setup_githooks ## Setup and run main application
	@echo "$(GREEN)🏁Running main application...$(RESET)"
	@$(PYTHON) main.py
	@echo "$(GREEN)✅ Main application run completed.$(RESET)"

docs: ## Run docs with bun
	@echo "$(GREEN)📚Running docs...$(RESET)"
	@cd docs && bun run dev
	@echo "$(GREEN)✅ Docs run completed.$(RESET)"


########################################################
# Run Tests
########################################################

TEST_TARGETS = tests/

### Testing
test: check_uv ## Run all pytest tests
	@echo "$(GREEN)🧪Running Target Tests...$(RESET)"
	$(TEST) $(TEST_TARGETS)
	@echo "$(GREEN)✅Target Tests Passed.$(RESET)"

test_fast: check_uv ## Run fast tests (exclude slow/nondeterministic)
	@echo "$(GREEN)🧪Running Fast Tests...$(RESET)"
	$(TEST) -m "not slow and not nondeterministic" $(TEST_TARGETS)
	@echo "$(GREEN)✅Fast Tests Passed.$(RESET)"

test_slow: check_uv ## Run slow tests only
	@echo "$(GREEN)🧪Running Slow Tests...$(RESET)"
	@$(TEST) -m "slow" $(TEST_TARGETS); \
	status=$$?; \
	if [ $$status -eq 5 ]; then \
		echo "$(YELLOW)⚠️ No slow tests collected.$(RESET)"; \
		exit 0; \
	fi; \
	exit $$status

test_nondeterministic: check_uv ## Run nondeterministic tests only
	@echo "$(GREEN)🧪Running Nondeterministic Tests...$(RESET)"
	@$(TEST) -m "nondeterministic" $(TEST_TARGETS); \
	status=$$?; \
	if [ $$status -eq 5 ]; then \
		echo "$(YELLOW)⚠️ No nondeterministic tests collected.$(RESET)"; \
		exit 0; \
	fi; \
	exit $$status

test_flaky: check_uv ## Repeat fast tests to detect flaky tests
	@echo "$(GREEN)🧪Running Flaky Test Detection...$(RESET)"
	$(TEST) --count 2 -m "not slow and not nondeterministic" $(TEST_TARGETS)
	@echo "$(GREEN)✅Flaky Test Detection Passed.$(RESET)"


########################################################
# Cleaning
########################################################

# Linter will ignore these directories
IGNORE_LINT_DIRS = .venv|venv
LINE_LENGTH = 88

### Code Quality
install_tools: check_uv ## Install linting/formatting tools
	@echo "$(YELLOW)🔧Installing tools...$(RESET)"
	@uv tool install black --force
	@uv tool install ruff --force
	@uv tool install import-linter --force
	@uv tool install ty --force
	@uv tool install vulture --force
	@echo "$(GREEN)✅Tools installed.$(RESET)"

fmt: install_tools check_jq ## Format code with black and jq
	@echo "$(YELLOW)✨Formatting project with Black...$(RESET)"
	@uv tool run black --exclude '/($(IGNORE_LINT_DIRS))/' . --line-length $(LINE_LENGTH)
	@echo "$(YELLOW)✨Formatting JSONs with jq...$(RESET)"
	@count=0; \
	find . \( $(IGNORE_LINT_DIRS:%=-path './%' -prune -o) \) -type f -name '*.json' -print0 | \
	while IFS= read -r -d '' file; do \
		if jq . "$$file" > "$$file.tmp" 2>/dev/null && mv "$$file.tmp" "$$file"; then \
			count=$$((count + 1)); \
		else \
			rm -f "$$file.tmp"; \
		fi; \
	done; \
	echo "$(BLUE)$$count JSON file(s)$(RESET) formatted."; \
	echo "$(GREEN)✅Formatting completed.$(RESET)"

ruff: install_tools ## Run ruff linter
	@echo "$(YELLOW)🔍Running ruff...$(RESET)"
	@uv tool run ruff check
	@echo "$(GREEN)✅Ruff completed.$(RESET)"

vulture: install_tools ## Find dead code with vulture
	@echo "$(YELLOW)🔍Running Vulture...$(RESET)"
	@uv tool run vulture .
	@echo "$(GREEN)✅Vulture completed.$(RESET)"

import_lint: install_tools ## Enforce module boundaries with import-linter
	@echo "$(YELLOW)🔍Running Import Linter...$(RESET)"
	@uv tool run --from import-linter lint-imports
	@echo "$(GREEN)✅Import Linter completed.$(RESET)"

ty: install_tools ## Run type checker
	@echo "$(YELLOW)🔍Running Typer...$(RESET)"
	@uv run ty check
	@echo "$(GREEN)✅Typer completed.$(RESET)"

docs_lint: ## Lint docs links
	@echo "$(YELLOW)🔍Linting docs links...$(RESET)"
	@cd docs && bun run lint:links
	@echo "$(GREEN)✅Docs linting completed.$(RESET)"

agents_validate: ## Validate AGENTS.md content
	@echo "$(YELLOW)🔍Validating AGENTS.md...$(RESET)"
	@$(PYTHON) scripts/validate_agents_md.py
	@echo "$(GREEN)✅AGENTS.md validation completed.$(RESET)"

ci: ruff vulture import_lint ty docs_lint ## Run all CI checks (ruff, vulture, import_lint, ty, docs_lint)
	@echo "$(GREEN)✅CI checks completed.$(RESET)"

########################################################
# Dependencies
########################################################

requirements:
	@echo "$(YELLOW)🔍Checking requirements...$(RESET)"
	@cp requirements-dev.lock requirements.txt
	@echo "$(GREEN)✅Requirements checked.$(RESET)"
