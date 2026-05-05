---
description: Dual-tool (Claude Code + Codex CLI) skill, subagent, and rule sync layout
globs:
  - ".claude/**"
  - ".agents/**"
  - ".codex/**"
---

# Codex ↔ Claude skill & subagent sync

This repo is dual-tool: both Claude Code and Codex CLI are expected to work. Skills and subagents are shared where possible. Read this before creating, editing, or moving any skill or subagent in this repo.

## Layout

```
.agents/skills/<name>/SKILL.md        # single source - both tools auto-discover
.claude/skills/<name>                 # symlink -> ../../.agents/skills/<name>
.claude/agents/<name>.md              # source of truth (markdown + YAML frontmatter)
.codex/agents/<name>.toml             # GENERATED from the .md; commit it
scripts/sync_agent_config.py          # converter (uv run)
.claude/rules/<name>.md               # source of truth (prose + globs frontmatter)
.agents/rules/<name>.md               # symlink → ../../.claude/rules/<name>.md
```

Codex auto-scans `.agents/skills/` walking up from cwd to repo root. Claude auto-scans `.claude/skills/`. The symlink is the only reason both find the same file.

## Skills: the shared-frontmatter rule

Every `SKILL.md` under `.agents/skills/` MUST be readable by both tools. The overlap is narrow - stick to it:

**Always safe (both tools):**
- `name` - required, lowercase-hyphens, ≤64 chars
- `description` - required, ≤250 chars, written for implicit matching
- Plain markdown body

**Claude-only - DO NOT use in shared skills:**
- `allowed-tools:` - Codex has no equivalent
- `context: fork`, `agent:`, `model:`, `effort:`, `hooks:`, `paths:`, `shell:`, `argument-hint`, `disable-model-invocation`, `user-invocable`
- `$ARGUMENTS`, `$1`, `$2`, ... - Claude substitutes these at runtime; Codex passes them through literally
- `` !`shell command` `` and ```` ```! ```` blocks - Claude preprocesses; Codex does not
- `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}` - Claude-only interpolations

**Codex-only - OK to include (Claude ignores unknown keys):**
- Sibling `agents/openai.yaml` for Codex UI metadata, invocation policy, tool dependencies

If a skill genuinely needs Claude-only features, keep it at `.claude/skills/<name>/` as a real directory (no symlink) and do not mirror it to `.agents/skills/`. Note this with a `<!-- claude-only -->` comment at the top of the body.

## Subagents: convert, don't symlink

The formats are structurally different:
- Claude: `.claude/agents/<name>.md` - YAML frontmatter (`name`, `description`, `tools`, `model`) + markdown body as system prompt
- Codex: `.codex/agents/<name>.toml` - TOML with `name`, `description`, `developer_instructions = """..."""` (body as triple-quoted string)

Rules:
- `.claude/agents/*.md` is the **source of truth**. Never hand-edit `.codex/agents/*.toml`.
- Run `make sync-agent-config` after editing a subagent. The pre-commit hook will refuse the commit if the generated TOML is out of date.
- Claude-only frontmatter keys (`tools`, `model`) don't translate - document tool expectations in the prose body instead so both sides pick them up.
- Inside the body, avoid literal `"""` sequences (they'd close the TOML string); the converter escapes them but it's easier to just not use them.

## Rules: symlink, don't convert

Rules sync in the **opposite direction** from skills:
- `.claude/rules/<name>.md` is the **source of truth**. Claude auto-discovers rules here.
- `.agents/rules/<name>.md` is a symlink mirror, created by `make sync-agent-config`.

The inversion is necessary because Claude is the primary consumer of rules today. `.agents/rules/` is a forward-looking mirror in case a cross-tool standard emerges.

Rule frontmatter uses `globs:` (not `paths:`) to scope when the rule attaches. Example:

```yaml
---
globs:
  - "src/api/**"
description: API route conventions
---
```

Read the `new-agent-rule` skill before creating a rule.

## Do not try to sync these

- `.codex/rules/*.rules` - Codex permission DSL (Starlark). Separate from `.claude/rules/` prose rules; maintain independently.
- `.claude/commands/*.md` - Claude-only; Codex has no slash-command runtime.
- `CLAUDE.md` vs `AGENTS.md` - both auto-read by their respective tool; keep them as separate documents, though content may overlap.

## Tooling

- `make sync-agent-config` - idempotent. Creates missing `.claude/skills/` symlinks for every shared skill under `.agents/skills/`, creates `.agents/rules/` symlinks for every rule under `.claude/rules/`, regenerates `.codex/agents/*.toml` from `.claude/agents/*.md`, auto-prunes dangling symlinks and orphan TOMLs silently.
- Pre-commit: [`prek`](https://prek.j178.dev/installation/), configured in `prek.toml` at repo root. Register once per clone with `prek install`. Runs `make sync-agent-config` then fails the commit if it produced drift.
- Python scripts in `scripts/` use `uv` and PEP 723 inline metadata for standalones.

## When adding a new skill or subagent

The `manage-agent-config` skill (at `.agents/skills/manage-agent-config/`) has the full decision tree and is invoked automatically when an agent touches any of these directories. The short version:

1. Shared skill (works in both tools) → `.agents/skills/<name>/SKILL.md`. Run `make sync-agent-config`.
2. Claude-only skill (uses `$ARGUMENTS`, `allowed-tools`, etc.) → `.claude/skills/<name>/SKILL.md` as a real directory. No symlink.
3. Subagent → edit `.claude/agents/<name>.md`. Never hand-edit `.codex/agents/*.toml`. Run `make sync-agent-config`. Commit both files.
4. Delete or rename → edit/remove the source, then `make sync-agent-config` cleans up the mirror.
5. New rule → write `.claude/rules/<name>.md` with `globs:` frontmatter. Run `make sync-agent-config`. The `.agents/rules/` symlink appears.
