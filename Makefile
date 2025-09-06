# ANSI color codes
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
BLUE=\033[0;34m
RESET=\033[0m

PYTHON=uv run
TEST=uv run pytest
PROJECT_ROOT=.

########################################################
# Initialization: Delete later
########################################################

banner: check_uv
	@echo "$(YELLOW)🔍Generating banner...$(RESET)"
	@uv run python -m init.generate_banner
	@echo "$(GREEN)✅Banner generated.$(RESET)"


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

setup: check_uv
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

all: setup setup_githooks
	@echo "$(GREEN)🏁Running main application...$(RESET)"
	@$(PYTHON) main.py
	@echo "$(GREEN)✅ Main application run completed.$(RESET)"


########################################################
# Run Tests
########################################################

TEST_TARGETS = tests/

# Tests
test: check_uv
	@echo "$(GREEN)🧪Running Target Tests...$(RESET)"
	$(TEST) $(TEST_TARGETS)
	@echo "$(GREEN)✅Target Tests Passed.$(RESET)"


########################################################
# Cleaning
########################################################

# Linter will ignore these directories
IGNORE_LINT_DIRS = .venv|venv
LINE_LENGTH = 88

install_tools: check_uv
	@echo "$(YELLOW)🔧Installing tools...$(RESET)"
	@uv tool install black --force
	@uv tool install ruff --force
	@uv tool install ty --force
	@uv tool install vulture --force
	@echo "$(GREEN)✅Tools installed.$(RESET)"

fmt: install_tools check_jq
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

ruff: install_tools
	@echo "$(YELLOW)🔍Running ruff...$(RESET)"
	@uv tool run ruff check
	@echo "$(GREEN)✅Ruff completed.$(RESET)"

vulture: install_tools
	@echo "$(YELLOW)🔍Running Vulture...$(RESET)"
	@uv tool run vulture .
	@echo "$(GREEN)✅Vulture completed.$(RESET)"

ty: install_tools
	@echo "$(YELLOW)🔍Running Typer...$(RESET)"
	@uv tool run ty check
	@echo "$(GREEN)✅Typer completed.$(RESET)"

########################################################
# Publishing
########################################################

build:
	@echo "$(YELLOW)🔨Building package...$(RESET)"
	@uv build

publish-test: build
	@echo "$(YELLOW)🚀Publishing to TestPyPI...$(RESET)"
	@uv run twine upload --repository testpypi dist/*

publish: build
	@echo "$(YELLOW)🚀Publishing to PyPI...$(RESET)"
	@uv run twine upload dist/*

########################################################
# Dependencies
########################################################

requirements:
	@echo "$(YELLOW)🔍Checking requirements...$(RESET)"
	@cp requirements-dev.lock requirements.txt
	@echo "$(GREEN)✅Requirements checked.$(RESET)"
