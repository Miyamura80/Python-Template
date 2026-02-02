from __future__ import annotations

import pathlib
from collections.abc import Iterable, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)
SKIP_DIRS = {
    ".git",
    ".venv",
    ".uv_cache",
    ".uv-cache",
    ".uv_tools",
    ".uv-tools",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
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
        if any(part in SKIP_DIRS for part in rel.parts):
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
