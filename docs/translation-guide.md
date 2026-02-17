# Translation Guide

Authoritative rules for the automated Jules translation workflow.
Jules **must** read this file before translating any docs.

## Glossary - NEVER translate these terms

Keep the following in English (untranslated) in every locale.

### Product & brand names

- Python Template
- MCP (Model Context Protocol)
- Fumadocs

### Security & feature terms

- ACL / Access Control Level
- SIEM
- PII
- DLP
- SSO / SCIM
- webhook

### Technical identifiers (never translate)

- CLI commands, flags, and arguments (e.g. `--verbose`, `npm install`)
- API endpoints and HTTP methods
- Environment variable names
- File paths and URLs
- Code snippets and fenced code blocks
- Configuration keys (JSON / YAML keys)
- CSS class names, hex colour codes

## File naming convention

| Type             | Pattern                          | Example                                    |
|------------------|----------------------------------|--------------------------------------------|
| English (source) | `<name>.mdx`                     | `docs/content/docs/index.mdx`              |
| Translation      | `<name>.<lang>.mdx`              | `docs/content/docs/index.ja.mdx`           |
| Section metadata | `meta.json` / `meta.<lang>.json` | `docs/content/docs/meta.ja.json`           |

## Translation PR rules

1. Preserve all Markdown / MDX structure: headings, tables, code blocks,
   admonitions, frontmatter, and JSX components.
2. Preserve anchor IDs, link targets, and `href` values verbatim.
3. If content was removed in English, remove it in every translation.
4. If a translation file is missing, create it from scratch.
5. Never modify English source files in a translation PR.
6. Never modify files outside `docs/content/`.
7. For `meta.json` files in each section directory, create or update
   `meta.<lang>.json`. Translate the `"title"` field but keep the `"pages"`
   array values unchanged (they are file identifiers, not user-facing text).
