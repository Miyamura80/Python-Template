from __future__ import annotations

import pathlib
from collections.abc import Iterable, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)
ROOT_SKIP_DIRS = {
    ".git",
    ".venv",
    ".uv_cache",
    ".uv-cache",
    ".uv_tools",
    ".uv-tools",
    ".cache",
    "node_modules",
    ".next",
}
RECURSIVE_SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_PATH_PREFIXES = {
    ("docs", ".next"),
    ("docs", "node_modules"),
}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp4",
    ".mov",
    ".mp3",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".ckpt",
    ".bin",
    ".pyc",
    ".pyo",
    ".db",
}


def iter_text_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_parts = rel.parts
        if rel_parts and rel_parts[0] in ROOT_SKIP_DIRS:
            continue
        if any(rel_parts[: len(prefix)] == prefix for prefix in SKIP_PATH_PREFIXES):
            continue
        dir_parts = rel_parts[:-1]
        if any(part in RECURSIVE_SKIP_DIRS for part in dir_parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def find_em_dashes(path: pathlib.Path) -> Sequence[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line:
            lines.append((lineno, line))
    return lines


def main() -> int:
    violations: list[tuple[pathlib.Path, int, str]] = []
    for path in iter_text_files(REPO_ROOT):
        for lineno, line in find_em_dashes(path):
            violations.append((path.relative_to(REPO_ROOT), lineno, line.strip()))
    if violations:
        print(
            f"AI writing check failed: {EM_DASH!r} (em dash) detected in the repository"
        )
        for rel_path, lineno, snippet in violations:
            print(f"{rel_path}:{lineno}: {snippet}")
        print("Please remove the em dash or explain why it is acceptable.")
        return 1
    print("AI writing check passed (no em dash found).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
