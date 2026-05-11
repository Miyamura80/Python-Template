---
paths:
  - "CLAUDE.md"
  - "AGENTS.md"
---

# Editing CLAUDE.md

`CLAUDE.md` is loaded into every Claude Code session. Every line costs context. Treat it like a hot path: dense, accurate, no fat.

`AGENTS.md` is often a symlink or copy of `CLAUDE.md` - check before editing; if linked, editing one edits both.

## Validation

Repos commonly enforce structure (required headings, banned characters, link checks) via Make targets, scripts, or pre-commit hooks. Before committing, run whatever the repo defines locally - don't rely on CI to catch it. If the repo has no validation, the hard requirement is just: don't break the section headings other tools rely on.

## Where it goes

Before adding to root `CLAUDE.md`, check whether it belongs somewhere else:

- **Always relevant in this repo** -> root `CLAUDE.md`.
- **Scoped to a subtree** -> nested `CLAUDE.md` / `AGENTS.md` inside that subtree.
- **Sometimes relevant, situation-triggered** -> a skill (`.claude/skills/<name>/SKILL.md`), loaded on demand.
- **Triggered by editing specific files** -> a path-scoped rule (`.claude/rules/<name>.md` with `paths:` frontmatter), like this file.
- **Must happen deterministically** -> a hook (pre-commit, `.claude/settings.json`), not prose. Hooks are deterministic; CLAUDE.md is advisory and Claude can ignore it.

If root `CLAUDE.md` crosses ~200 lines, that's a smell: push specifics into nested files, skills, or rules.

## What earns its place

Include a line only if it's all of:
1. **Non-obvious** - not derivable from a directory name, a standard tool, or sensible defaults.
2. **Non-rot-prone** - won't go stale on the next refactor (avoid file enumerations, "currently we have X, Y, Z" lists).
3. **Non-rediscoverable** - a future Claude can't trivially get it from one `Read` or one `ls`.
4. **Not duplicated elsewhere in the file** - if the same fact appears in multiple sections or in a code block, pick one.

Categories that typically earn their place:
- The project's headline architecture idea or organizing principle.
- Layering / dependency-direction rules.
- `file:line` anchors for key entrypoints.
- Non-standard infra choices a reader would assume differently by default.
- Project-specific conventions (commit message format, naming patterns, long-running task patterns).
- Gotchas (deprecated APIs, fast-evolving specs, build quirks).
- Disambiguations for terms or concepts that are easy to get wrong.

## What to cut

- ASCII architecture diagrams - they're a low-density way to transmit structure to a coding agent (lots of tokens for what a few bullets convey). Prefer compact bullet layering; put the diagram in `README.md` if humans want it.
- Restating directory purpose when the name already says it (`db/` is the database, `tests/` is tests, `.github/workflows/` is CI workflows).
- Listing files that mirror a directory - they rot, and `ls` is one tool call.
- Implementation walkthroughs. A `file:line` anchor + one sentence is enough; details are rediscoverable in one `Read`.
- Style rules already enforced by the linter/formatter. The Code Style section should just point at the linter config.
- Boilerplate intros ("This file provides guidance to Claude Code...").
- Sections duplicated by a dedicated section below.
- Code-block comments that restate the next line.
- Deterministic must-happens better expressed as a hook (pre-commit, `settings.json`) - prose is advisory, hooks are enforced.
- Self-evident platitudes ("write clean code", "follow best practices").
