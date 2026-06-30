"""Collect AGENTS.md baselines for find_agents_baseline.py."""

from __future__ import annotations

import os
from pathlib import Path

from find_agents_git import last_commit, tracked_files


def walk_agent_files(repo: Path, agent_file: str) -> set[str]:
    matches: set[str] = set()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        if agent_file not in files:
            continue
        path = Path(root, agent_file)
        matches.add(path.relative_to(repo).as_posix())
    return matches


def scope_for(relpath: str) -> str:
    parent = Path(relpath).parent.as_posix()
    return "." if parent == "." else parent


def missing_agent_result(repo: Path, agent_file: str) -> dict[str, object]:
    return {
        "repo": str(repo),
        "agent_files": [
            {
                "path": agent_file,
                "scope": ".",
                "last_commit": None,
                "exists": (repo / agent_file).exists(),
                "tracked": False,
            }
        ],
        "warnings": [f"No tracked {agent_file} files found; initial setup is required."],
    }


def baseline_entry(repo: Path, path: str, tracked: set[str]) -> dict[str, object]:
    is_tracked = path in tracked
    return {
        "path": path,
        "scope": scope_for(path),
        "last_commit": last_commit(repo, path, is_tracked),
        "exists": (repo / path).exists(),
        "tracked": is_tracked,
    }


def collect_baselines(repo: Path, agent_file: str) -> dict[str, object]:
    warnings: list[str] = []
    tracked = tracked_files(repo)
    found = walk_agent_files(repo, agent_file)
    agent_paths = sorted(found | {path for path in tracked if Path(path).name == agent_file})

    if not agent_paths:
        return missing_agent_result(repo, agent_file)

    entries = []
    for path in agent_paths:
        if path not in tracked:
            warnings.append(f"{path} exists but is not tracked by git.")
        entries.append(baseline_entry(repo, path, tracked))

    return {"repo": str(repo), "agent_files": entries, "warnings": warnings}
