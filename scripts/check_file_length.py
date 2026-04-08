from __future__ import annotations

import pathlib
import tomllib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
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


def load_config() -> tuple[int, set[str]]:
    pyproject = REPO_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    cfg = data.get("tool", {}).get("file_length", {})
    max_lines = cfg.get("max_lines", 500)
    exclude = set(cfg.get("exclude", []))
    return max_lines, exclude


def main() -> int:
    max_lines, exclude = load_config()
    violations: list[tuple[pathlib.Path, int]] = []

    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT)
        parts = rel.parts
        if parts[0] in ROOT_SKIP_DIRS:
            continue
        if any(part in RECURSIVE_SKIP_DIRS for part in parts[:-1]):
            continue
        if rel.as_posix() in exclude:
            continue
        line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if line_count > max_lines:
            violations.append((rel, line_count))

    if violations:
        print(
            f"File length check failed: {len(violations)} file(s) exceed {max_lines} lines"
        )
        for rel_path, count in sorted(violations):
            print(f"  {rel_path}: {count} lines")
        print(
            "Refactor large files into smaller modules, "
            "or add to [tool.file_length] exclude in pyproject.toml."
        )
        return 1

    print(f"File length check passed (all files <= {max_lines} lines).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
