---
name: wait
description: Pause execution for a requested number of minutes by sleeping one-minute increments to avoid exceeding shell timeouts.
user_invocable: true
triggers:
  - /wait
  - wait
---

# Wait Skill

Use this skill whenever the user asks the assistant to pause or wait for a few minutes during a task. Instead of issuing a single long `sleep` command (which often hits the 2-minute shell timeout), run one-minute sleeps repeatedly for the requested duration.

## Workflow

1. **Determine the wait time.** Parse the user’s request for a duration expressed in minutes. If the request is vague, ask a clarifying question (e.g., “How many minutes should I wait?”) before running commands.
2. **Enforce sane limits.** If the user requests a very large number of minutes, warn them and offer to break the wait into smaller chunks or confirm before proceeding.
3. **Execute sequential Bash sleeps.** For each of the requested N minutes, issue a separate `bash` tool call with `sleep 60`. Before each call, report the upcoming iteration as `executing sleep: i/N: bash sleep 60` so observers know how many sleeps will run. Avoid bundling the sleeps into a single script; the goal is to keep every sleeping command under the 2-minute timeout.

4. **Report completion.** Once the loop finishes, notify the user that the wait is over and resume the primary task.

## Error handling

- If the shell command fails (e.g., `sleep` unavailable), report the failure and stop waiting.
- If the user changes their mind mid-wait, cancel the remaining iterations and explain how much time was actually spent waiting.
