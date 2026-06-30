"""Docs index checks for repository knowledge stores."""

from __future__ import annotations

from pathlib import Path

from check_knowledge_common import add_check, rel
from check_knowledge_traversal import knowledge_files


def docs_directories(repo: Path) -> list[Path]:
    docs_dirs = set()
    for path in knowledge_files(repo):
        for parent in path.parents:
            if parent == repo.parent:
                break
            if parent.name == "docs":
                docs_dirs.add(parent)
    return sorted(docs_dirs)


def check_docs_indexes(repo: Path, checks: list[dict[str, str]]) -> None:
    scoped_files = set(knowledge_files(repo))
    for docs_dir in docs_directories(repo):
        if not (docs_dir / "index.md").exists():
            add_check(
                checks,
                "missing-docs-index",
                "warning",
                rel(repo, docs_dir),
                "docs directory exists without index.md",
            )
            continue
        if (docs_dir / "index.md") not in scoped_files:
            add_check(
                checks,
                "missing-docs-index",
                "warning",
                rel(repo, docs_dir),
                "docs directory exists without tracked index.md",
            )
