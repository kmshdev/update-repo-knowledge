"""Docs index checks for repository knowledge stores."""

from __future__ import annotations

import os
from pathlib import Path

from check_knowledge_common import add_check, rel


def check_docs_indexes(repo: Path, checks: list[dict[str, str]]) -> None:
    for root, dirs, _files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        if Path(root).name != "docs":
            continue
        docs_dir = Path(root)
        if not (docs_dir / "index.md").exists():
            add_check(
                checks,
                "missing-docs-index",
                "warning",
                rel(repo, docs_dir),
                "docs directory exists without index.md",
            )
