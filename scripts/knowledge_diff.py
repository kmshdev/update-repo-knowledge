#!/usr/bin/env python3
"""Summarize repository changes since AGENTS.md baseline commits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from knowledge_diff_git import load_baseline  # noqa: E402
from knowledge_diff_summary import summarize  # noqa: E402


def print_text(result: dict[str, object]) -> None:
    for change in result["changes"]:
        print(
            f"{change['status']} {change['path']} "
            f"[{change['doc_impact']}; {change['agent_file']}]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Path to a git repository")
    parser.add_argument("--baseline-json", required=True, help="Path to baseline JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2

    try:
        result = summarize(repo, load_baseline(Path(args.baseline_json)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
