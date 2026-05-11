# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0", "tomli_w>=1.0"]
# ///
"""Sync Claude ↔ Codex skills and subagents.

- Symlinks `.claude/skills/<name>` → `../../.agents/skills/<name>` for every
  directory under `.agents/skills/`.
- Regenerates `.codex/agents/<name>.toml` from each `.claude/agents/<name>.md`.
- Auto-prunes dangling symlinks and orphaned TOMLs silently.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import tomli_w
import yaml

REPO = Path(__file__).resolve().parent.parent
SHARED_SKILLS = REPO / ".agents" / "skills"
CLAUDE_SKILLS = REPO / ".claude" / "skills"
CLAUDE_AGENTS = REPO / ".claude" / "agents"
CODEX_AGENTS = REPO / ".codex" / "agents"

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)
CLAUDE_ONLY_KEYS = {
    "tools",
    "model",
    "color",
    "allowed-tools",
    "disable-model-invocation",
}

SHARED_SKILL_FORBIDDEN_KEYS = {
    "allowed-tools",
    "disable-model-invocation",
    "user-invocable",
    "context",
    "agent",
    "model",
    "effort",
    "hooks",
    "paths",
    "shell",
    "argument-hint",
}
SHARED_SKILL_FORBIDDEN_BODY_PATTERNS = [
    (re.compile(r"\$ARGUMENTS\b"), "$ARGUMENTS substitution"),
    (re.compile(r"\$[1-9]\b"), "positional arg substitution ($1, $2, ...)"),
    (re.compile(r"\$\{CLAUDE_[A-Z_]+\}"), "${CLAUDE_*} interpolation"),
    (re.compile(r"!`[^`]+`"), "!`cmd` shell preprocessing"),
]
SHARED_SKILL_RAW_BODY_PATTERNS = [
    (re.compile(r"^```!\s*$", re.MULTILINE), "```! shell preprocessing block"),
]


def parse_md(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise SystemExit(f"{path}: missing YAML frontmatter")
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise SystemExit(
            f"{path}: frontmatter must be a YAML mapping, got {type(meta).__name__}"
        )
    return meta, re.sub(r"^(?:\r?\n)+", "", m.group(2))


def render_toml(meta: dict, body: str, source: Path | None = None) -> str:
    if not meta.get("name"):
        where = f"{source}: " if source else ""
        raise SystemExit(f"{where}missing `name` in frontmatter")
    data = {
        "name": str(meta["name"]),
        "description": str(meta.get("description") or ""),
        "developer_instructions": body.rstrip() + "\n",
    }
    out = tomli_w.dumps(data, multiline_strings=True)
    extras = {k: v for k, v in meta.items() if k in CLAUDE_ONLY_KEYS}
    if extras:
        out += "\n# Claude-only frontmatter (preserved for reference, not used by Codex):\n"
        for k, v in extras.items():
            out += f"# {k} = {v!r}\n"
    return out


def _strip_code(text: str) -> str:
    text = re.sub(
        r"^[ ]{0,3}(`{3,}).*?^[ ]{0,3}\1`*", "", text, flags=re.DOTALL | re.MULTILINE
    )
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == "`":
            preceded_by_bang = bool(out) and out[-1] == "!"
            run = 0
            while i + run < n and text[i + run] == "`":
                run += 1
            close = text.find("`" * run, i + run)
            if close == -1 or any(
                text[i + run + k] == "\n" for k in range(close - i - run)
            ):
                out.append(text[i : i + run])
                i += run
            elif preceded_by_bang and run == 1:
                # Preserve `!`cmd`` verbatim so the Claude-only shell-preprocessing
                # pattern can still match after code stripping.
                out.append(text[i : close + run])
                i = close + run
            else:
                i = close + run
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def validate_shared_skill(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.relative_to(REPO)}: missing SKILL.md"]
    try:
        meta, body = parse_md(skill_md)
    except SystemExit as e:
        return [str(e)]
    errs: list[str] = []
    bad_keys = SHARED_SKILL_FORBIDDEN_KEYS & set(meta.keys())
    if bad_keys:
        errs.append(
            f"{skill_md.relative_to(REPO)}: Claude-only frontmatter keys in shared skill: {sorted(bad_keys)}"
        )
    for pat, label in SHARED_SKILL_RAW_BODY_PATTERNS:
        if pat.search(body):
            errs.append(
                f"{skill_md.relative_to(REPO)}: body uses Claude-only feature: {label}"
            )
    scan_body = _strip_code(body)
    for pat, label in SHARED_SKILL_FORBIDDEN_BODY_PATTERNS:
        if pat.search(scan_body):
            errs.append(
                f"{skill_md.relative_to(REPO)}: body uses Claude-only feature: {label}"
            )
    if not meta.get("name"):
        errs.append(f"{skill_md.relative_to(REPO)}: missing `name` in frontmatter")
    if not meta.get("description"):
        errs.append(
            f"{skill_md.relative_to(REPO)}: missing `description` in frontmatter"
        )
    return errs


def _validate_all_shared_skills(names: set[str]) -> None:
    errors: list[str] = []
    for name in names:
        errors.extend(validate_shared_skill(SHARED_SKILLS / name))
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)


def _materialize_symlink(name: str) -> str | None:
    link = CLAUDE_SKILLS / name
    target = Path("..") / ".." / ".agents" / "skills" / name
    if link.is_symlink():
        if os.path.normpath(os.readlink(link)) == os.path.normpath(str(target)):
            return None
        link.unlink()
    elif link.exists():
        raise SystemExit(
            f"ERROR: name collision - .claude/skills/{name} is a real directory (Claude-only skill) "
            f"but .agents/skills/{name} also exists (shared skill). Resolve by removing one of them."
        )
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as e:
        raise SystemExit(
            f"ERROR: could not create symlink {link.relative_to(REPO)} -> {target}: {e}. "
            "If you're on Windows, enable Developer Mode or run your shell as Administrator "
            "so Python can create symlinks."
        ) from e
    return f"symlinked {link.relative_to(REPO)}"


def sync_skill_symlinks() -> list[str]:
    changes: list[str] = []
    shared_existed = SHARED_SKILLS.exists()
    if not shared_existed:
        SHARED_SKILLS.mkdir(parents=True)
    CLAUDE_SKILLS.mkdir(parents=True, exist_ok=True)

    wanted = {p.name for p in SHARED_SKILLS.iterdir() if p.is_dir()}
    _validate_all_shared_skills(wanted)

    for name in wanted:
        change = _materialize_symlink(name)
        if change:
            changes.append(change)

    # If .agents/skills/ was missing entirely (sparse checkout, manual rm) and we
    # just created it empty, refuse to prune - otherwise we'd silently delete every
    # Claude symlink. User-created symlinks elsewhere are unaffected either way.
    if not shared_existed and not wanted:
        return changes

    for link in CLAUDE_SKILLS.iterdir():
        if link.is_symlink() and link.name not in wanted:
            link.unlink()
            changes.append(f"pruned dangling {link.relative_to(REPO)}")
    return changes


def sync_agents() -> list[str]:
    changes: list[str] = []
    CODEX_AGENTS.mkdir(parents=True, exist_ok=True)
    CLAUDE_AGENTS.mkdir(parents=True, exist_ok=True)

    wanted = set()
    for md in CLAUDE_AGENTS.glob("*.md"):
        meta, body = parse_md(md)
        toml = CODEX_AGENTS / f"{md.stem}.toml"
        new = render_toml(meta, body, source=md.relative_to(REPO))
        if not toml.exists() or toml.read_text() != new:
            toml.write_text(new)
            changes.append(f"wrote {toml.relative_to(REPO)}")
        wanted.add(toml.name)

    for toml in CODEX_AGENTS.glob("*.toml"):
        if toml.name not in wanted:
            toml.unlink()
            changes.append(f"pruned orphan {toml.relative_to(REPO)}")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Still write changes, but exit non-zero when any were made. Used by the pre-commit hook.",
    )
    args = parser.parse_args()

    changes = sync_skill_symlinks() + sync_agents()
    for c in changes:
        print(c)
    if args.check and changes:
        print(
            "sync-agent-config introduced changes; stage them and commit again.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
