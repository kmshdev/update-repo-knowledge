"""Git and baseline helpers for knowledge_diff.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
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


def load_baseline(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "agent_files" not in data:
        raise ValueError("baseline JSON must contain an agent_files array")
    return data


def normalize_status(line: str) -> tuple[str, str] | None:
    if not line.strip():
        return None
    parts = line.split("\t")
    status = parts[0]
    path = parts[-1]
    return status, path


def changed_files(repo: Path, baseline: str, scope: str) -> list[tuple[str, str]]:
    scope_arg = "." if scope == "." else scope
    committed = run_git(
        repo,
        ["diff", "--name-status", f"{baseline}..HEAD", "--", scope_arg],
    ).stdout.splitlines()
    working = run_git(repo, ["diff", "--name-status", "--", scope_arg]).stdout.splitlines()
    staged = run_git(
        repo,
        ["diff", "--cached", "--name-status", "--", scope_arg],
    ).stdout.splitlines()

    seen: dict[str, str] = {}
    for line in [*committed, *working, *staged]:
        parsed = normalize_status(line)
        if not parsed:
            continue
        status, path = parsed
        seen[path] = status
    return sorted((status, path) for path, status in seen.items())
