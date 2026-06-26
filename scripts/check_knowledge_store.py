#!/usr/bin/env python3
"""Validate basic repository knowledge-store health."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ADAPTER_POINTER_PATTERN = re.compile(r"\bAGENTS\.md\b|canonical", re.IGNORECASE)
ADAPTER_GENERATED_HEADER_LINES = 10
ADAPTER_SHORT_POINTER_MAX_CHARS = 500
ADAPTER_SHORT_POINTER_MAX_LINES = 5
ADAPTER_GENERATED_MARKER_PATTERN = re.compile(
    r"\b(auto[- ]?generated|generated|do not edit|source)\b",
    re.IGNORECASE,
)
ADAPTER_DECORATIVE_LINE_PATTERN = re.compile(r"^(#|<!--|-->|//)")
ADAPTER_FILES = {
    ".cursorrules",
    "CLAUDE.md",
    "GEMINI.md",
}


def add_check(
    checks: list[dict[str, str]],
    check_id: str,
    severity: str,
    path: str,
    message: str,
) -> None:
    checks.append({"id": check_id, "severity": severity, "path": path, "message": message})


def rel(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def adapter_shape(adapter_text: str) -> str:
    stripped = adapter_text.strip()
    if not ADAPTER_POINTER_PATTERN.search(stripped):
        return "missing-pointer"

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    header = "\n".join(lines[:ADAPTER_GENERATED_HEADER_LINES])
    if ADAPTER_GENERATED_MARKER_PATTERN.search(header):
        return "generated-pointer"

    content_lines = [
        line for line in lines if not ADAPTER_DECORATIVE_LINE_PATTERN.search(line)
    ]
    if (
        len(lines) <= ADAPTER_SHORT_POINTER_MAX_LINES
        and len(stripped) <= ADAPTER_SHORT_POINTER_MAX_CHARS
        and all(ADAPTER_POINTER_PATTERN.search(line) for line in content_lines)
    ):
        return "short-pointer"

    return "extra-content"


def markdown_files(repo: Path) -> list[Path]:
    results: list[Path] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in files:
            if name.endswith(".md"):
                results.append(Path(root, name))
    return sorted(results)


def is_external_link(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme) or target.startswith("#")


def check_markdown_links(repo: Path, checks: list[dict[str, str]]) -> None:
    for path in markdown_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LINK_PATTERN.finditer(text):
            raw_target = match.group(1).strip()
            if not raw_target or is_external_link(raw_target):
                continue
            clean_target = raw_target.split("#", 1)[0].strip()
            if not clean_target:
                continue
            target_path = (path.parent / unquote(clean_target)).resolve()
            try:
                target_path.relative_to(repo)
            except ValueError:
                continue
            exists = target_path.exists()
            if target_path.is_dir():
                exists = (target_path / "index.md").exists()
            if not exists:
                add_check(
                    checks,
                    "broken-markdown-link",
                    "error",
                    rel(repo, path),
                    f"Link target {clean_target} does not exist",
                )


def check_docs_indexes(repo: Path, checks: list[dict[str, str]]) -> None:
    for root, dirs, _files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        if Path(root).name != "docs":
            continue
        docs_dir = Path(root)
        if not (docs_dir / "index.md").exists():
            add_check(
                checks,
                "missing-docs-index",
                "warning",
                rel(repo, docs_dir),
                "docs directory exists without index.md",
            )


def check_agent_files(repo: Path, checks: list[dict[str, str]]) -> None:
    root_agents = repo / "AGENTS.md"
    if not root_agents.exists():
        add_check(
            checks,
            "missing-root-agents",
            "error",
            "AGENTS.md",
            "Root AGENTS.md is missing; initial knowledge-store setup is required",
        )

    agent_dirs: list[Path] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name != ".git"]
        base = Path(root)
        if "AGENTS.md" in files:
            agent_dirs.append(base)

        adapter_files = sorted(name for name in files if name in ADAPTER_FILES)
        if not adapter_files:
            continue

        nearest_agents = nearest_agent_file(base, agent_dirs)
        for adapter_name in adapter_files:
            adapter = base / adapter_name
            if adapter.is_symlink():
                continue
            adapter_text = adapter.read_text(encoding="utf-8", errors="replace")
            shape = adapter_shape(adapter_text)
            if shape in {"short-pointer", "generated-pointer"}:
                continue

            nearest_label = rel(repo, nearest_agents) if nearest_agents else "nearest AGENTS.md"
            if shape == "extra-content":
                add_check(
                    checks,
                    "adapter-extra-content",
                    "warning",
                    rel(repo, adapter),
                    (
                        f"{adapter_name} points to {nearest_label} but contains "
                        "additional instruction content; keep adapters as short "
                        "canonical pointers or declare this adapter canonical in "
                        "AGENTS.md"
                    ),
                )
                continue

            add_check(
                checks,
                "adapter-drift",
                "warning",
                rel(repo, adapter),
                f"{adapter_name} is not an adapter pointer to {nearest_label}",
            )


def nearest_agent_file(path: Path, agent_dirs: list[Path]) -> Path | None:
    candidates = [
        agent_dir
        for agent_dir in agent_dirs
        if path == agent_dir or agent_dir in path.parents
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: len(candidate.parts)) / "AGENTS.md"


def validate(repo: Path) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    check_agent_files(repo, checks)
    check_docs_indexes(repo, checks)
    check_markdown_links(repo, checks)
    errors = sum(1 for check in checks if check["severity"] == "error")
    warnings = sum(1 for check in checks if check["severity"] == "warning")
    return {
        "repo": str(repo),
        "checks": checks,
        "summary": {"errors": errors, "warnings": warnings},
    }


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
        for check in result["checks"]:
            print(f"{check['severity']}: {check['path']}: {check['message']}")
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
