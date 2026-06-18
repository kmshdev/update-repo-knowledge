#!/usr/bin/env python3
"""Summarize repository changes since AGENTS.md baseline commits."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


NO_DOC_NAMES = {
    ".DS_Store",
    "Cargo.lock",
    "Gemfile.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "yarn.lock",
}

NO_DOC_SUFFIXES = {
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
}

NO_DOC_PATH_PARTS = {
    ".cache",
    "__pycache__",
    "coverage",
    "dist",
    "generated",
    "node_modules",
}


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


def path_under_scope(path: str, scope: str) -> bool:
    return scope == "." or path == scope or path.startswith(f"{scope}/")


def nearest_agent(path: str, agents: list[dict[str, object]]) -> dict[str, object] | None:
    candidates = [entry for entry in agents if path_under_scope(path, str(entry["scope"]))]
    if not candidates:
        return None
    return max(candidates, key=lambda entry: len(str(entry["scope"])))


def classify(path: str, status: str) -> tuple[str, str]:
    parts = set(Path(path).parts)
    name = Path(path).name
    suffix = Path(path).suffix.lower()
    if (
        name in NO_DOC_NAMES
        or suffix in NO_DOC_SUFFIXES
        or parts.intersection(NO_DOC_PATH_PARTS)
    ):
        return "no-doc-impact", "generated, binary, lock, or local metadata file changed"
    if status.startswith("D"):
        return "uncertain", "deleted file may invalidate docs or agent routes"
    if name in {"AGENTS.md", "CLAUDE.md"}:
        return "review", "agent instruction file changed"
    if path.startswith("docs/") or "/docs/" in path:
        return "review", "documentation file changed"
    return "review", "source or project file changed under covered scope"


def summarize(repo: Path, baseline_data: dict[str, object]) -> dict[str, object]:
    agents = [
        entry
        for entry in baseline_data.get("agent_files", [])
        if isinstance(entry, dict) and entry.get("last_commit")
    ]

    if not agents:
        return {
            "repo": str(repo),
            "baseline": None,
            "changes": [],
            "summary": {"changed_files": 0, "review_required": 0, "no_doc_impact": 0},
            "warnings": ["No tracked AGENTS.md baseline commit found; initial setup is required."],
        }

    all_changes: dict[str, dict[str, object]] = {}
    for entry in agents:
        baseline = str(entry["last_commit"])
        scope = str(entry["scope"])
        for status, path in changed_files(repo, baseline, scope):
            owner = nearest_agent(path, agents) or entry
            impact, reason = classify(path, status)
            all_changes[path] = {
                "path": path,
                "status": status,
                "agent_file": owner["path"],
                "doc_impact": impact,
                "reason": reason,
            }

    changes = [all_changes[path] for path in sorted(all_changes)]
    review_required = sum(1 for item in changes if item["doc_impact"] in {"review", "uncertain"})
    no_doc_impact = sum(1 for item in changes if item["doc_impact"] == "no-doc-impact")
    baselines = sorted({str(entry["last_commit"]) for entry in agents})
    return {
        "repo": str(repo),
        "baseline": baselines[0] if len(baselines) == 1 else None,
        "changes": changes,
        "summary": {
            "changed_files": len(changes),
            "review_required": review_required,
            "no_doc_impact": no_doc_impact,
        },
    }


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
        for change in result["changes"]:
            print(
                f"{change['status']} {change['path']} "
                f"[{change['doc_impact']}; {change['agent_file']}]"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
