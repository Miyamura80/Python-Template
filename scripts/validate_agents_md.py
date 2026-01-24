#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "Project Overview",
    "Common Commands",
    "Architecture",
    "Code Style",
    "Configuration Pattern",
]


def find_agents_file(repo_root: Path) -> Path | None:
    for filename in ["AGENTS.md", "CLAUDE.md"]:
        path = repo_root / filename
        if path.exists():
            return path
    return None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    agents_path = find_agents_file(repo_root)
    if agents_path is None:
        print("AGENTS.md or CLAUDE.md is missing.")
        return 1

    content = agents_path.read_text().strip()
    if not content:
        print(f"{agents_path.name} is empty.")
        return 1

    missing_sections = []
    for section in REQUIRED_SECTIONS:
        pattern = re.compile(rf"^##+\s+{re.escape(section)}\s*$", re.MULTILINE)
        if not pattern.search(content):
            missing_sections.append(section)

    if missing_sections:
        missing_list = ", ".join(missing_sections)
        print(f"{agents_path.name} is missing required sections: {missing_list}.")
        return 1

    print(f"{agents_path.name} validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
