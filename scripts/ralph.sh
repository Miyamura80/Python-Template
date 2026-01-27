#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool opencode|amp|claude] [max_iterations]

set -e

# Parse arguments
TOOL="opencode"  # Default to opencode
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    *)
      # Assume it's max_iterations if it's a number
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

# Validate tool choice
if [[ "$TOOL" != "opencode" && "$TOOL" != "amp" && "$TOOL" != "claude" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'opencode', 'amp' or 'claude'."
  exit 1
fi

# Check for jq dependency
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: 'jq' is not installed but required by this script."
  echo "Please install it (e.g., 'brew install jq' or 'sudo apt-get install jq')."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_DIR="$SCRIPT_DIR/ralph"
PRD_FILE="$RALPH_DIR/prd.json"
PROGRESS_FILE="$RALPH_DIR/progress.txt"
ARCHIVE_DIR="$RALPH_DIR/archive"
LAST_BRANCH_FILE="$RALPH_DIR/.last-branch"

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    # Archive the previous run
    DATE=$(date +%Y-%m-%d)
    # Strip "ralph/" prefix from branch name for folder
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    
    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"
    
    # Reset progress file for new run
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Run the selected tool with the ralph prompt
  if [[ "$TOOL" == "opencode" ]]; then
    # opencode run: use prompt from prompt.md
    if [ -f "$RALPH_DIR/prompt.md" ]; then
      OUTPUT=$(opencode run "$(cat "$RALPH_DIR/prompt.md")" 2>&1 | tee /dev/stderr) || true
    else
      echo "Error: $RALPH_DIR/prompt.md not found. Create this file or use a different tool."
      echo "Example: ./ralph.sh --tool claude"
      exit 1
    fi
  elif [[ "$TOOL" == "amp" ]]; then
    if [ -f "$RALPH_DIR/prompt.md" ]; then
      OUTPUT=$(cat "$RALPH_DIR/prompt.md" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
    else
      echo "Error: $RALPH_DIR/prompt.md not found. Create this file or use a different tool."
      exit 1
    fi
  else
    # Claude Code: use --dangerously-skip-permissions for autonomous operation, --print for output
    if [ -f "$RALPH_DIR/prompt.md" ]; then
      OUTPUT=$(claude --dangerously-skip-permissions --print < "$RALPH_DIR/prompt.md" 2>&1 | tee /dev/stderr) || true
    else
      echo "Error: $RALPH_DIR/prompt.md not found. Create this file or use a different tool."
      exit 1
    fi
  fi
  
  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi
  
  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
