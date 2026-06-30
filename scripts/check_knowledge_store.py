#!/usr/bin/env python3
"""Validate basic repository knowledge-store health."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_knowledge_adapters import check_agent_files  # noqa: E402
from check_knowledge_docs import check_docs_indexes  # noqa: E402
from check_knowledge_links import check_markdown_links  # noqa: E402


def count_severity(checks: list[dict[str, str]], severity: str) -> int:
    return sum(1 for check in checks if check["severity"] == severity)


def validate(repo: Path) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    check_agent_files(repo, checks)
    check_docs_indexes(repo, checks)
    check_markdown_links(repo, checks)
    return {
        "repo": str(repo),
        "checks": checks,
        "summary": {
            "errors": count_severity(checks, "error"),
            "warnings": count_severity(checks, "warning"),
        },
    }


def print_text(result: dict[str, object]) -> None:
    for check in result["checks"]:
        print(f"{check['severity']}: {check['path']}: {check['message']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Path to a git repository")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"Repository path does not exist: {repo}", file=sys.stderr)
        return 2

    result = validate(repo)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_text(result)
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
