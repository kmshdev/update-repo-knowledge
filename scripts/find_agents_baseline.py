#!/usr/bin/env python3
"""Find tracked AGENTS.md files and their last update commits."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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


def walk_agent_files(repo: Path, agent_file: str) -> set[str]:
    matches: set[str] = set()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        if agent_file not in files:
            continue
        path = Path(root, agent_file)
        matches.add(path.relative_to(repo).as_posix())
    return matches


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


def scope_for(relpath: str) -> str:
    parent = Path(relpath).parent.as_posix()
    return "." if parent == "." else parent


def collect_baselines(repo: Path, agent_file: str) -> dict[str, object]:
    warnings: list[str] = []
    tracked = tracked_files(repo)
    found = walk_agent_files(repo, agent_file)
    agent_paths = sorted(found | {path for path in tracked if Path(path).name == agent_file})

    if not agent_paths:
        root_agent = agent_file
        return {
            "repo": str(repo),
            "agent_files": [
                {
                    "path": root_agent,
                    "scope": ".",
                    "last_commit": None,
                    "exists": (repo / root_agent).exists(),
                    "tracked": False,
                }
            ],
            "warnings": [f"No tracked {agent_file} files found; initial setup is required."],
        }

    entries = []
    for path in agent_paths:
        is_tracked = path in tracked
        if not is_tracked:
            warnings.append(f"{path} exists but is not tracked by git.")
        entries.append(
            {
                "path": path,
                "scope": scope_for(path),
                "last_commit": last_commit(repo, path, is_tracked),
                "exists": (repo / path).exists(),
                "tracked": is_tracked,
            }
        )

    return {"repo": str(repo), "agent_files": entries, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Path to a git repository")
    parser.add_argument("--agent-file", default="AGENTS.md", help="Agent file name to inspect")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2
    if not is_git_repo(repo):
        print(f"Not a git repository: {repo}", file=sys.stderr)
        return 2

    result = collect_baselines(repo, args.agent_file)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for entry in result["agent_files"]:
            print(f"{entry['path']}: {entry['last_commit'] or 'no tracked baseline'}")
        for warning in result["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
