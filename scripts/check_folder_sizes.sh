#!/usr/bin/env bash
#
# Enforce a file-count limit on source folders (non-recursive). Shared by
# .github/workflows/folder-size.yaml and prek.toml.
#
# Usage:
#   check_folder_sizes.sh [file ...]   # check folders containing the given files
#   check_folder_sizes.sh --all        # scan every folder in the tree
#
# Thresholds: warn at WARN files-per-folder, error at ERROR. Override via
# FOLDER_WARN_THRESHOLD / FOLDER_ERROR_THRESHOLD env vars (namespaced so
# they don't collide with check_large_files.sh).
# Exit 1 on non-grandfathered errors, 0 on warnings-only or clean.
#
# If $GITHUB_STEP_SUMMARY is set, a markdown summary is appended to it.

set -euo pipefail

WARN_THRESHOLD="${FOLDER_WARN_THRESHOLD:-20}"
ERROR_THRESHOLD="${FOLDER_ERROR_THRESHOLD:-35}"

GRANDFATHERED=()

EXCLUDE_PATH_RE='(^|/)(node_modules|__pycache__|\.venv|venv|visual-tests|e2e|tests|test|__tests__|\.git|dist|build)(/|$)'
ALEMBIC_RE='(^|/)alembic[^/]*/versions(/|$)'

is_grandfathered() {
  local target="$1"
  for g in "${GRANDFATHERED[@]}"; do
    [ "$target" = "$g" ] && return 0
  done
  return 1
}

should_skip() {
  local f="$1"
  [ -z "$f" ] && return 0
  [ "$f" = "." ] && return 0
  echo "$f" | grep -qE "$EXCLUDE_PATH_RE" && return 0
  echo "$f" | grep -qE "$ALEMBIC_RE" && return 0
  return 1
}

count_folder() {
  find "$1" -mindepth 1 -maxdepth 1 -type f \
    -name '*.py' \
    -not -name 'test_*.py' \
    -not -name 'conftest.py' \
    -not -name 'vulture_whitelist.py' \
    | wc -l
}

collect_all_folders() {
  find . -type d \
    -not -path './.git/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/.venv/*' \
    -not -path '*/venv/*' \
    | sed 's|^\./||'
}

folder_list=$(mktemp)
trap 'rm -f "$folder_list"' EXIT

if [ "${1:-}" = "--all" ]; then
  collect_all_folders > "$folder_list"
else
  for f in "$@"; do
    [ -z "$f" ] && continue
    dirname "$f"
  done | sort -u > "$folder_list"
fi

warnings=0
errors=0
warn_list=""
error_list=""

while IFS= read -r folder; do
  folder="${folder#./}"
  should_skip "$folder" && continue
  [ ! -d "$folder" ] && continue

  count=$(count_folder "$folder")

  if [ "$count" -gt "$ERROR_THRESHOLD" ]; then
    if is_grandfathered "$folder"; then
      warnings=$((warnings + 1))
      warn_list="${warn_list}| \`${folder}/\` | ${count} | :warning: exceeds ${ERROR_THRESHOLD} (grandfathered) |\n"
    else
      errors=$((errors + 1))
      error_list="${error_list}| \`${folder}/\` | ${count} | :x: exceeds ${ERROR_THRESHOLD} |\n"
    fi
  elif [ "$count" -gt "$WARN_THRESHOLD" ]; then
    warnings=$((warnings + 1))
    warn_list="${warn_list}| \`${folder}/\` | ${count} | :warning: exceeds ${WARN_THRESHOLD} |\n"
  fi
done < "$folder_list"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ] && { [ "$errors" -gt 0 ] || [ "$warnings" -gt 0 ]; }; then
  {
    echo "## Folder Size Report"
    echo ""
    echo "| Folder | Files | Status |"
    echo "|--------|-------|--------|"
    [ "$errors" -gt 0 ] && printf '%b' "$error_list"
    [ "$warnings" -gt 0 ] && printf '%b' "$warn_list"
    echo ""
    echo "**Thresholds:** warn at ${WARN_THRESHOLD} files, error at ${ERROR_THRESHOLD} files. Counts immediate \`.py\` children only - subfolders are the fix, not the problem."
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
  echo "::error::${errors} folder(s) exceed the ${ERROR_THRESHOLD}-file error threshold" >&2
  format_list "$error_list" >&2
fi
if [ "$warnings" -gt 0 ]; then
  echo "::warning::${warnings} folder(s) exceed the ${WARN_THRESHOLD}-file warning threshold" >&2
  format_list "$warn_list" >&2
fi
if [ "$errors" -eq 0 ] && [ "$warnings" -eq 0 ]; then
  echo "All folders are within the ${WARN_THRESHOLD}-file limit."
fi

[ "$errors" -gt 0 ] && exit 1
exit 0
