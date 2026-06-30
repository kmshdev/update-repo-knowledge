#!/usr/bin/env python3
"""Find tracked AGENTS.md files and their last update commits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from find_agents_collect import collect_baselines  # noqa: E402
from find_agents_git import is_git_repo  # noqa: E402


def print_text(result: dict[str, object]) -> None:
    for entry in result["agent_files"]:
        print(f"{entry['path']}: {entry['last_commit'] or 'no tracked baseline'}")
    for warning in result["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)


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
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
