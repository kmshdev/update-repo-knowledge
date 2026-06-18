#!/usr/bin/env python3
"""Add optional ast-grep structural hints to knowledge_diff.py output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


NOTE = "AST hints identify touched structures only; inspect source/tests before updating docs."

HUNK_PATTERN = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

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

LANGUAGE_BY_EXTENSION = {
    ".bash": "bash",
    ".bats": "bash",
    ".c": "c",
    ".cc": "cpp",
    ".cjs": "javascript",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".cxx": "cpp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".go": "go",
    ".h": "c",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".hs": "haskell",
    ".htm": "html",
    ".html": "html",
    ".hxx": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".mjs": "javascript",
    ".php": "php",
    ".phtml": "php",
    ".py": "python",
    ".pyw": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sc": "scala",
    ".scala": "scala",
    ".sh": "bash",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".yaml": "yaml",
    ".yml": "yaml",
}

LANGUAGE_BY_NAME = {
    "bashrc": "bash",
}

KIND_PROFILES = {
    "bash": ["function_definition"],
    "c": ["function_definition", "struct_specifier", "enum_specifier"],
    "cpp": ["function_definition", "class_specifier", "struct_specifier", "enum_specifier"],
    "csharp": ["class_declaration", "method_declaration", "struct_declaration"],
    "css": ["rule_set", "at_rule"],
    "elixir": ["call"],
    "go": ["function_declaration", "method_declaration", "type_declaration"],
    "haskell": ["function", "type_synomym", "data_type"],
    "html": ["element", "script_element", "style_element"],
    "java": ["class_declaration", "method_declaration", "interface_declaration"],
    "javascript": ["function_declaration", "class_declaration", "method_definition"],
    "json": ["object", "pair", "array"],
    "kotlin": ["function_declaration", "class_declaration", "object_declaration"],
    "lua": ["function_declaration", "function_definition"],
    "php": ["function_definition", "class_declaration", "method_declaration"],
    "python": ["function_definition", "class_definition", "decorated_definition"],
    "ruby": ["method", "class", "module"],
    "rust": ["function_item", "struct_item", "enum_item", "impl_item", "trait_item"],
    "scala": ["function_definition", "class_definition", "object_definition", "trait_definition"],
    "swift": [
        "function_declaration",
        "class_declaration",
        "struct_declaration",
        "enum_declaration",
    ],
    "typescript": ["function_declaration", "class_declaration", "method_definition"],
    "tsx": ["function_declaration", "class_declaration", "method_definition"],
    "yaml": ["block_mapping_pair", "block_mapping", "block_sequence_item"],
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


def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(args)} failed: {message}")
    return result


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def language_for_path(path: str) -> Optional[str]:
    target = Path(path)
    name = target.name.lower()
    if name in LANGUAGE_BY_NAME:
        return LANGUAGE_BY_NAME[name]
    return LANGUAGE_BY_EXTENSION.get(target.suffix.lower())


def changed_ranges_from_diff(diff_text: str) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    for line in diff_text.splitlines():
        match = HUNK_PATTERN.search(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        end = start if count == 0 else start + count - 1
        ranges.append({"start": start, "end": end})
    return ranges


def path_under_scope(path: str, scope: str) -> bool:
    return scope == "." or path == scope or path.startswith(f"{scope}/")


def nearest_agent(path: str, agents: list[dict[str, object]]) -> Optional[dict[str, object]]:
    candidates = [entry for entry in agents if path_under_scope(path, str(entry["scope"]))]
    if not candidates:
        return None
    return max(candidates, key=lambda entry: len(str(entry["scope"])))


def changed_ranges_for_path(repo: Path, baseline: str, path: str) -> list[dict[str, int]]:
    result = run_git(repo, ["diff", "--unified=0", baseline, "--", path])
    return changed_ranges_from_diff(result.stdout)


def is_generated_or_binary(path: str) -> bool:
    target = Path(path)
    parts = set(target.parts)
    return target.suffix.lower() in NO_DOC_SUFFIXES or bool(parts.intersection(NO_DOC_PATH_PARTS))


def find_sg(sg_path: Optional[str]) -> dict[str, object]:
    path = sg_path or shutil.which("sg")
    if not path or not Path(path).exists():
        return {"available": False, "path": path, "version": None}
    result = run_command([path, "--version"], check=False)
    if result.returncode != 0:
        return {"available": False, "path": path, "version": None}
    return {"available": True, "path": path, "version": result.stdout.strip()}


def ranges_intersect(left: dict[str, int], right: dict[str, int]) -> bool:
    return left["start"] <= right["end"] and right["start"] <= left["end"]


def node_range(match: dict[str, object]) -> dict[str, int]:
    raw_range = match.get("range")
    if not isinstance(raw_range, dict):
        return {"start": 0, "end": 0}
    start = raw_range.get("start")
    end = raw_range.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return {"start": 0, "end": 0}
    return {"start": int(start.get("line", 0)) + 1, "end": int(end.get("line", 0)) + 1}


def preview_text(match: dict[str, object]) -> str:
    text = str(match.get("text") or match.get("lines") or "")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return ""


def ast_grep_matches(
    sg_path: str,
    file_path: Path,
    language: str,
    kind: str,
) -> tuple[list[dict], str]:
    result = run_command(
        [
            sg_path,
            "run",
            "-k",
            kind,
            "-l",
            language,
            "--json=stream",
            str(file_path),
        ],
        check=False,
    )
    if result.returncode != 0:
        return [], result.stderr.strip() or result.stdout.strip()

    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        matches.append(json.loads(line))
    return matches, ""


def build_hints(
    sg_path: str,
    file_path: Path,
    language: str,
    changed_ranges: list[dict[str, int]],
) -> tuple[list[dict[str, object]], list[str]]:
    hints: list[dict[str, object]] = []
    errors: list[str] = []
    seen: set[tuple[str, int, int, str]] = set()
    for kind in KIND_PROFILES.get(language, []):
        matches, error = ast_grep_matches(sg_path, file_path, language, kind)
        if error:
            errors.append(error)
            continue
        for match in matches:
            current_range = node_range(match)
            if not any(ranges_intersect(current_range, changed) for changed in changed_ranges):
                continue
            preview = preview_text(match)
            key = (kind, current_range["start"], current_range["end"], preview)
            if key in seen:
                continue
            seen.add(key)
            hints.append({"kind": kind, "range": current_range, "preview": preview})
    hints.sort(key=lambda item: (item["range"]["end"] - item["range"]["start"], item["kind"]))
    return hints[:20], errors


def base_change(change: dict[str, object]) -> dict[str, object]:
    return {
        "path": change.get("path"),
        "status": change.get("status"),
        "agent_file": change.get("agent_file"),
        "doc_impact": change.get("doc_impact"),
        "language": None,
        "ast_status": "",
        "changed_ranges": [],
        "hints": [],
        "note": NOTE,
    }


def skip_entry(
    change: dict[str, object],
    status: str,
    language: Optional[str] = None,
) -> dict[str, object]:
    entry = base_change(change)
    entry["language"] = language
    entry["ast_status"] = status
    return entry


def analyze_change(
    repo: Path,
    change: dict[str, object],
    agents: list[dict[str, object]],
    sg_info: dict[str, object],
) -> tuple[dict[str, object], str]:
    path = str(change.get("path") or "")
    doc_impact = str(change.get("doc_impact") or "")
    status = str(change.get("status") or "")

    if doc_impact not in {"review", "uncertain"}:
        return skip_entry(change, "not-review-required"), "skipped"
    if status.startswith("D"):
        return skip_entry(change, "deleted"), "skipped"
    if is_generated_or_binary(path):
        return skip_entry(change, "generated-or-binary"), "skipped"

    language = language_for_path(path)
    if not language:
        return skip_entry(change, "unsupported-language"), "unsupported"

    current_path = repo / path
    if not current_path.exists():
        return skip_entry(change, "missing", language), "skipped"

    owner = nearest_agent(path, agents)
    baseline = str(owner.get("last_commit")) if owner else ""
    if not baseline:
        return skip_entry(change, "no-baseline", language), "skipped"

    changed_ranges = changed_ranges_for_path(repo, baseline, path)
    entry = base_change(change)
    entry["language"] = language
    entry["changed_ranges"] = changed_ranges

    if not changed_ranges:
        entry["ast_status"] = "no-changed-ranges"
        return entry, "skipped"
    if not sg_info["available"]:
        entry["ast_status"] = "sg-missing"
        return entry, "eligible"

    hints, errors = build_hints(str(sg_info["path"]), current_path, language, changed_ranges)
    entry["hints"] = hints
    if hints:
        entry["ast_status"] = "ok"
    elif errors:
        entry["ast_status"] = "ast-grep-error"
        entry["errors"] = errors[:5]
    else:
        entry["ast_status"] = "parsed-no-hints"
    return entry, "analyzed"


def summarize(
    repo: Path,
    baseline_data: dict[str, object],
    diff_data: dict[str, object],
    sg_path: Optional[str] = None,
) -> dict[str, object]:
    agents = [
        entry
        for entry in baseline_data.get("agent_files", [])
        if isinstance(entry, dict) and entry.get("last_commit")
    ]
    sg_info = find_sg(sg_path)
    changes = []
    summary = {"eligible_files": 0, "analyzed_files": 0, "unsupported_files": 0, "skipped_files": 0}

    for change in diff_data.get("changes", []):
        if not isinstance(change, dict):
            continue
        entry, state = analyze_change(repo, change, agents, sg_info)
        changes.append(entry)
        if state == "eligible":
            summary["eligible_files"] += 1
        elif state == "analyzed":
            summary["eligible_files"] += 1
            summary["analyzed_files"] += 1
        elif state == "unsupported":
            summary["unsupported_files"] += 1
        else:
            summary["skipped_files"] += 1

    return {"repo": str(repo), "sg": sg_info, "summary": summary, "changes": changes}


def print_text(result: dict[str, object]) -> None:
    for change in result["changes"]:
        print(
            f"{change['ast_status']} {change['path']} "
            f"[{change['language'] or 'unknown'}; {len(change['hints'])} hints]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Path to a git repository")
    parser.add_argument("--baseline-json", required=True, help="Path to baseline JSON")
    parser.add_argument("--knowledge-diff-json", required=True, help="Path to knowledge diff JSON")
    parser.add_argument("--sg-path", help="Path to the ast-grep CLI")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

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
