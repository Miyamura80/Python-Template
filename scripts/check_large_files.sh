#!/usr/bin/env bash
#
# Enforce a line-count limit on source files. Shared by
# .github/workflows/large-files.yaml and prek.toml.
#
# Usage:
#   check_large_files.sh [file ...]   # check the given files
#   check_large_files.sh --all        # scan the whole tree
#
# Thresholds: warn at WARN lines, error at ERROR lines. Override via
# LARGE_FILE_WARN_THRESHOLD / LARGE_FILE_ERROR_THRESHOLD env vars
# (namespaced so they don't collide with check_folder_sizes.sh).
# Exit 1 on errors, 0 on warnings-only or clean.
#
# If $GITHUB_STEP_SUMMARY is set, a markdown summary is appended to it.

set -euo pipefail

WARN_THRESHOLD="${LARGE_FILE_WARN_THRESHOLD:-500}"
ERROR_THRESHOLD="${LARGE_FILE_ERROR_THRESHOLD:-800}"

EXCLUDE_PATH_RE='(^|/)(node_modules|__pycache__|\.venv|venv|visual-tests|e2e|tests|test|__tests__|\.git)(/|$)'
ALEMBIC_RE='(^|/)alembic[^/]*/versions(/|$)'
EXCLUDE_NAME_RE='(^test_[^/]+\.py|^conftest\.py|^vulture_whitelist\.py)$'

is_source_file() {
  case "$1" in
    *.py) return 0 ;;
    *) return 1 ;;
  esac
}

is_excluded() {
  local f="$1" base
  echo "$f" | grep -qE "$EXCLUDE_PATH_RE" && return 0
  echo "$f" | grep -qE "$ALEMBIC_RE" && return 0
  base=$(basename "$f")
  echo "$base" | grep -qE "$EXCLUDE_NAME_RE" && return 0
  return 1
}

collect_all() {
  find . -type f -name '*.py' \
    -not -path './.git/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/.venv/*' \
    -not -path '*/venv/*' \
    | sed 's|^\./||'
}

files=()
if [ "${1:-}" = "--all" ]; then
  mapfile -t files < <(collect_all)
else
  files=("$@")
fi

warnings=0
errors=0
warn_list=""
error_list=""

for file in "${files[@]}"; do
  [ -z "$file" ] && continue
  [ ! -f "$file" ] && continue
  is_source_file "$file" || continue
  is_excluded "$file" && continue

  lines=$(wc -l < "$file")
  if [ "$lines" -gt "$ERROR_THRESHOLD" ]; then
    errors=$((errors + 1))
    error_list="${error_list}| \`${file}\` | ${lines} | :x: exceeds ${ERROR_THRESHOLD} |\n"
  elif [ "$lines" -gt "$WARN_THRESHOLD" ]; then
    warnings=$((warnings + 1))
    warn_list="${warn_list}| \`${file}\` | ${lines} | :warning: exceeds ${WARN_THRESHOLD} |\n"
  fi
done

if [ -n "${GITHUB_STEP_SUMMARY:-}" ] && { [ "$errors" -gt 0 ] || [ "$warnings" -gt 0 ]; }; then
  {
    echo "## Large File Report"
    echo ""
    echo "| File | Lines | Status |"
    echo "|------|-------|--------|"
    [ "$errors" -gt 0 ] && printf '%b' "$error_list"
    [ "$warnings" -gt 0 ] && printf '%b' "$warn_list"
    echo ""
    echo "**Thresholds:** warn at ${WARN_THRESHOLD} lines, error at ${ERROR_THRESHOLD} lines"
  } >> "$GITHUB_STEP_SUMMARY"
fi

format_list() {
  if command -v column >/dev/null 2>&1; then
    printf '%b' "$1" | column -t -s '|'
  else
    printf '%b' "$1"
  fi
}

if [ "$errors" -gt 0 ]; then
  echo "::error::${errors} file(s) exceed the ${ERROR_THRESHOLD}-line error threshold" >&2
  format_list "$error_list" >&2
fi
if [ "$warnings" -gt 0 ]; then
  echo "::warning::${warnings} file(s) exceed the ${WARN_THRESHOLD}-line warning threshold" >&2
  format_list "$warn_list" >&2
fi
if [ "$errors" -eq 0 ] && [ "$warnings" -eq 0 ]; then
  echo "All source files are within the ${WARN_THRESHOLD}-line limit."
fi

[ "$errors" -gt 0 ] && exit 1
exit 0
