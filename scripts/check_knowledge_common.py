"""Shared helpers for check_knowledge_store.py."""

from __future__ import annotations

from pathlib import Path


def add_check(
    checks: list[dict[str, str]],
    check_id: str,
    severity: str,
    path: str,
    message: str,
) -> None:
    checks.append({"id": check_id, "severity": severity, "path": path, "message": message})


def rel(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()
