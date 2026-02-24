# Outdated Documentation Guideline

This document defines the rules Jules must follow when detecting and fixing
documentation drift in this repository.

## Philosophy

Documentation must accurately reflect the current state of the code. We fix
**factual inaccuracies only** - never rewrite style, tone, or structure. Every
fix must be backed by concrete evidence from the codebase.

## What Counts as Outdated Documentation

- **Wrong file paths**: References to files or directories that have been moved,
  renamed, or deleted.
- **Incorrect commands**: CLI commands, Make targets, or setup instructions that
  no longer work as described.
- **Stale API references**: Docstrings or docs describing function signatures,
  parameters, or return types that no longer match the actual code.
- **Deprecated patterns**: Code examples showing usage patterns that have been
  replaced (e.g., `datetime.utcnow()` instead of `datetime.now(timezone.utc)`).
- **Wrong configuration keys**: References to config keys that have been renamed
  or removed from `global_config.yaml` or `pyproject.toml`.
- **Broken cross-references**: Internal links between docs that point to
  non-existent anchors or files.
- **Incorrect version requirements**: Python version, dependency versions, or
  tool versions that don't match `pyproject.toml`.

## What Is NOT Outdated Documentation

Do **not** flag or modify:

- **Style preferences**: Wording choices, tone, or paragraph structure.
- **Aspirational content**: Roadmap items, planned features, or TODOs.
- **External links**: Links to third-party sites (these are checked by
  `make lint_links` separately).
- **Translation files**: Never edit `*.lang.mdx` or `meta.lang.json` files
  directly. The Jules Translation Sync workflow handles translations
  automatically when English sources change.
- **Generated content**: Auto-generated API docs, badges, or CI status lines.

## Translation Policy Alignment

This repository uses an automated Jules Translation Sync workflow. When you
fix English documentation:

1. **Only edit English source files** (e.g., `file.mdx`, not `file.ja.mdx`).
2. **Never create or modify translation files** - the translation workflow will
   pick up your English changes and translate them automatically.
3. **Preserve frontmatter and MDX structure** exactly as-is so translations
   remain aligned.
4. If you find a translation file that is outdated relative to its English
   source, note it in the PR description but do **not** fix it directly.

## Files to Scan

Priority order for drift detection:

1. `README.md` - Primary entry point, most visible.
2. `CLAUDE.md` - Agent instructions, must match actual project structure.
3. `docs/content/**/*.mdx` - English documentation pages only.
4. `AGENTS.md` - Agent configuration, if present.
5. Docstrings in `src/`, `common/`, `utils/` - Inline documentation.
6. `pyproject.toml` description and metadata fields.

## Validation Before Fixing

For each documentation fix, verify:

1. **Cross-reference the code**: Confirm the actual current behavior by reading
   the relevant source file. Never guess.
2. **Check git history**: If a file was recently moved, use the new path. If
   deleted, note the removal.
3. **Test commands**: For CLI/Make instructions, verify the command exists in the
   Makefile or CLI entry point.
4. **Config key existence**: For config references, verify the key exists in the
   current `global_config.yaml` or relevant config file.

## PR Requirements

- Title format: `docs: fix outdated documentation (automated weekly drift check)`
- Each fix must be listed in the PR description with:
  - File path and line range
  - What was wrong (old content)
  - What was fixed (new content)
  - Evidence file path showing the correct information
- If no outdated documentation is found, do **not** create a PR.
