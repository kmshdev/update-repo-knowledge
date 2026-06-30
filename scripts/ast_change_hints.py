#!/usr/bin/env python3
"""Add optional ast-grep structural hints to knowledge_diff.py output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ast_change_io import load_json  # noqa: E402
from ast_change_summary import summarize  # noqa: E402


def print_text(result: dict[str, object]) -> None:
    for change in result["changes"]:
        print(
            f"{change['ast_status']} {change['path']} "
            f"[{change['language'] or 'unknown'}; {len(change['hints'])} hints]"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Path to a git repository")
    parser.add_argument("--baseline-json", required=True, help="Path to baseline JSON")
    parser.add_argument("--knowledge-diff-json", required=True, help="Path to knowledge diff JSON")
    parser.add_argument("--sg-path", help="Path to the ast-grep CLI")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2

    try:
        result = summarize(
            repo,
            load_json(Path(args.baseline_json)),
            load_json(Path(args.knowledge_diff_json)),
            sg_path=args.sg_path,
        )
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
