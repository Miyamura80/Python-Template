# ANSI color codes
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
BLUE=\033[0;34m
RESET=\033[0m

PYTHON=rye run python
TEST=rye run pytest
PROJECT_ROOT=.

########################################################
# Check dependencies
########################################################

check_rye:
	@echo "$(YELLOW)Checking rye version...$(RESET)"
	@if ! command -v rye > /dev/null 2>&1; then \
		echo "$(RED)rye is not installed. Please install rye before proceeding.$(RESET)"; \
		exit 1; \
	else \
		rye --version; \
	fi

########################################################
# Python dependency-related
########################################################

update_python_dep: check_rye
	@echo "$(YELLOW)Updating python dependencies...$(RESET)"
	@rye sync

view_python_venv_size:
	@echo "$(YELLOW)Checking python venv size...$(RESET)"
	@cd .venv/lib/python3.11/site-packages && du -sh . && cd ../../../
	@echo "$(GREEN)Python venv size check completed.$(RESET)"

view_python_venv_size_by_libraries:
	@echo "$(YELLOW)Checking python venv size by libraries...$(RESET)"
	@cd .venv/lib/python3.11/site-packages && du -sh * | sort -h && cd ../../../
	@echo "$(GREEN)Python venv size by libraries check completed.$(RESET)"

########################################################
# Run Main Application
########################################################

all: update_python_dep
	@echo "$(GREEN)Running main application...$(RESET)"
	@$(PYTHON) main.py
	@echo "$(GREEN)Main application run completed.$(RESET)"


########################################################
# Run Tests
########################################################

TEST_TARGETS = tests/folder1 tests/folder2

# Tests
test: check_rye
	@echo "$(GREEN)Running Target Tests...$(RESET)"
	$(TEST) $(TEST_TARGETS)
	@echo "$(GREEN)Target Tests Passed.$(RESET)"


########################################################
# Linting
########################################################

# Linter will ignore these directories
IGNORE_LINT_DIRS = .venv|venv
LINE_LENGTH = 88

lint: check_rye
	@echo "$(YELLOW)Linting project with Black...$(RESET)"
	@rye run black --exclude '/($(IGNORE_LINT_DIRS))/' . --line-length $(LINE_LENGTH)
	@echo "$(GREEN)Linting completed.$(RESET)"

