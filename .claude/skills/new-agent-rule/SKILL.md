---
name: new-agent-rule
description: Guide for creating a new path-scoped .claude/rules/ file with proper globs frontmatter and structure.
---

# Creating a new path-scoped rule

Rules keep CLAUDE.md lean by scoping guidance to specific file paths. A rule only loads when the agent touches files matching its `globs:` pattern.

## When to create a rule

- Guidance applies to a specific directory or file pattern, not the whole repo
- The guidance is long enough that embedding it in CLAUDE.md would bloat the file
- Multiple agents (or future tools) should pick up the same guidance automatically

## Naming and location

- Source of truth: `.claude/rules/<name>.md`
- Name: `snake_case.md` describing the area (e.g., `api_routes.md`, `test_conventions.md`)
- Mirror: `.agents/rules/<name>.md` (symlink, created by `make sync-agent-config`)

## Frontmatter format

Use `globs:` (NOT `paths:` -- it has known silent-failure bugs):

```yaml
---
description: One-line summary of what this rule covers
globs:
  - "src/api/**"
  - "tests/api/**"
---
```

Pick the narrowest set of globs that covers the area. Overly broad globs waste context on unrelated tasks.

## Workflow

1. Check if CLAUDE.md already covers this guidance (if so, migrate it to a rule)
2. Write `.claude/rules/<name>.md` with `globs:` frontmatter
3. Run `make sync-agent-config` then `make ci`

## Anti-patterns

- Forgetting `globs:` frontmatter (rule loads on every task, defeating the purpose)
- Restating what CLAUDE.md already says (keep rules additive, not duplicative)
- Using `paths:` instead of `globs:` (known silent-failure bugs in Claude)
