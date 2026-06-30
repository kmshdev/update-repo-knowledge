"""Shared ignore-aware traversal for repository knowledge checks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


EXCLUDED_DIRS = {
    ".cache",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "generated",
    "node_modules",
    "venv",
}


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def is_git_worktree(repo: Path) -> bool:
    result = run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def tracked_and_unignored_files(repo: Path) -> list[Path]:
    result = run_git(repo, ["ls-files", "--cached", "--others", "--exclude-standard"])
    if result.returncode != 0:
        return []
    paths = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        paths.append(repo / line)
    return sorted(paths)


def fallback_files(repo: Path) -> list[Path]:
    paths: list[Path] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        base = Path(root)
        for name in files:
            paths.append(base / name)
    return sorted(paths)


def knowledge_files(repo: Path) -> list[Path]:
    """Return the intentionally scoped input files for knowledge-store checks."""
    if is_git_worktree(repo):
        return tracked_and_unignored_files(repo)
    return fallback_files(repo)
