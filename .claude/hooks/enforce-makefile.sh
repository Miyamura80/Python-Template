#!/bin/bash
set -euo pipefail

# PreToolUse hook: intercept commands that should use Makefile targets instead.
# Exit 0 with JSON deny = block the command and suggest an alternative.
# Exit 0 with no output = allow the command.

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')

# Block direct invocation of the AI writing check script
if [[ "$COMMAND" == *"check_ai_writing"* ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Do not run the AI writing check script directly. Instead, avoid using em dashes (U+2014) in any code or text you write. The check runs automatically via pre-commit hooks."
    }
  }'
  exit 0
fi

# Allow everything else
exit 0
