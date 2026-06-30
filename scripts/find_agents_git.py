"""Git helpers for find_agents_baseline.py."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git in repo and return captured text output."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result


def is_git_repo(repo: Path) -> bool:
    result = run_git(repo, ["rev-parse", "--is-inside-work-tree"], check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def tracked_files(repo: Path) -> set[str]:
    result = run_git(repo, ["ls-files", "-z"])
    return {item for item in result.stdout.split("\0") if item}


def last_commit(repo: Path, relpath: str, tracked: bool) -> str | None:
    if not tracked:
        return None
    result = run_git(
        repo,
        ["log", "--follow", "-n", "1", "--format=%H", "--", relpath],
        check=False,
    )
    commit = result.stdout.strip()
    return commit or None
