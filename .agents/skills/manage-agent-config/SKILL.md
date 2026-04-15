---
name: manage-agent-config
description: Use whenever creating, editing, renaming, or deleting any file under .claude/skills/, .claude/agents/, .agents/skills/, or .codex/agents/. Teaches the dual-tool Claude/Codex layout and reminds to run `make sync-agent-config`.
---

# Managing Claude ↔ Codex skills and subagents in this repo

This repo is dual-tool. Before you create or edit anything under `.claude/`, `.agents/`, or `.codex/`, read this and the detailed rule at `.claude/rules/codex-claude-sync.md`.

## Decision tree

**Creating a new skill?**

1. Does it need Claude-only features (`allowed-tools`, `$ARGUMENTS`, `` !`shell` `` preprocessing, `${CLAUDE_SKILL_DIR}`)?
   - **Yes** → `.claude/skills/<name>/SKILL.md` (real directory, no symlink). Claude-only.
   - **No** → `.agents/skills/<name>/SKILL.md`. Shared; `make sync-agent-config` creates the `.claude/skills/<name>` symlink.

**Creating a new subagent?**

- Always edit `.claude/agents/<name>.md` (markdown + YAML frontmatter). That is the source of truth.
- `.codex/agents/<name>.toml` is **generated** - never hand-edit.
- Run `make sync-agent-config` - the TOML appears.

**Renaming or deleting?**

- Rename or delete the source file (under `.agents/skills/` or `.claude/agents/`).
- Run `make sync-agent-config` - stale symlinks and orphaned TOMLs are pruned automatically.

## Frontmatter rules for shared skills

`.agents/skills/<name>/SKILL.md` must only use:

- `name` (required, lowercase-hyphens, ≤64 chars)
- `description` (required, ≤250 chars - Codex and Claude use this for implicit matching)
- Plain markdown body

Do **not** use any of these in a shared skill:

- `allowed-tools`, `disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `hooks`, `paths`, `shell`, `argument-hint`
- `$ARGUMENTS`, `$1`…`$N`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}` substitutions
- `` !`cmd` `` or ```` ```! ```` shell preprocessing blocks

All of those are Claude-only. In Codex they pass through literally and confuse the model. If you need them, make the skill Claude-only (see decision tree above).

## Subagent format notes

Claude `.md` frontmatter keys that don't exist in Codex (`tools`, `model`, `color`) are preserved as TOML comments in the generated `.codex/agents/<name>.toml` for human reference. They do not affect Codex behavior. If tool restrictions matter to the agent's job, describe them in the prose body so both tools read them.

## After any change

Always run `make sync-agent-config`. The prek pre-commit hook will block the commit otherwise. The script is idempotent and silent when there's nothing to do.
