#!/usr/bin/env python3
"""PreToolUse hook: intercept commands that should use Makefile targets instead."""

import json
import re
import sys


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def main() -> None:
    hook_input = json.loads(sys.stdin.read())
    command = hook_input.get("tool_input", {}).get("command", "")

    # Block direct invocation of the AI writing check script
    # Match only actual script execution, not mentions in strings
    if re.search(r"(uv\s+run\s+python|python3?|\./).*check_ai_writing\.py", command):
        deny(
            "Do not run the AI writing check script directly. "
            "Instead, avoid using em dashes (U+2014) in any code or text you write. "
            "The check runs automatically via pre-commit hooks."
        )


if __name__ == "__main__":
    main()
