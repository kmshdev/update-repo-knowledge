"""Classify changed files and attach AST hint data."""

from __future__ import annotations

from pathlib import Path

from ast_change_config import NOTE
from ast_change_hint_building import build_hints
from ast_change_io import changed_ranges_for_path
from ast_change_paths import is_generated_or_binary, language_for_path, nearest_agent


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
    language: str | None = None,
) -> dict[str, object]:
    entry = base_change(change)
    entry["language"] = language
    entry["ast_status"] = status
    return entry


def should_skip_before_language(
    change: dict[str, object],
    path: str,
) -> tuple[dict[str, object], str] | None:
    doc_impact = str(change.get("doc_impact", ""))
    status = str(change.get("status", ""))
    if doc_impact not in {"review", "uncertain"}:
        return skip_entry(change, "not-review-required"), "skipped"
    if status.startswith("D"):
        return skip_entry(change, "deleted"), "skipped"
    if is_generated_or_binary(path):
        return skip_entry(change, "generated-or-binary"), "skipped"
    return None


def baseline_for_path(path: str, agents: list[dict[str, object]]) -> str:
    owner = nearest_agent(path, agents)
    return str(owner.get("last_commit")) if owner else ""


def analyzed_entry(
    change: dict[str, object],
    language: str,
    changed_ranges: list[dict[str, int]],
) -> dict[str, object]:
    entry = base_change(change)
    entry["language"] = language
    entry["changed_ranges"] = changed_ranges
    return entry


def finalize_entry(
    entry: dict[str, object],
    sg_info: dict[str, object],
    repo: Path,
    path: str,
    language: str,
    changed_ranges: list[dict[str, int]],
) -> tuple[dict[str, object], str]:
    if not changed_ranges:
        entry["ast_status"] = "no-changed-ranges"
        return entry, "skipped"
    if not sg_info["available"]:
        entry["ast_status"] = "sg-missing"
        return entry, "eligible"

    hints, errors = build_hints(str(sg_info["path"]), repo / path, language, changed_ranges)
    entry["hints"] = hints
    if hints:
        entry["ast_status"] = "ok"
    elif errors:
        entry["ast_status"] = "ast-grep-error"
        entry["errors"] = errors[:5]
    else:
        entry["ast_status"] = "parsed-no-hints"
    return entry, "analyzed"


def analyze_change(
    repo: Path,
    change: dict[str, object],
    agents: list[dict[str, object]],
    sg_info: dict[str, object],
) -> tuple[dict[str, object], str]:
    path = str(change.get("path", ""))
    early_skip = should_skip_before_language(change, path)
    if early_skip:
        return early_skip

    language = language_for_path(path)
    if not language:
        return skip_entry(change, "unsupported-language"), "unsupported"
    if not (repo / path).exists():
        return skip_entry(change, "missing", language), "skipped"

    baseline = baseline_for_path(path, agents)
    if not baseline:
        return skip_entry(change, "no-baseline", language), "skipped"

    changed_ranges = changed_ranges_for_path(repo, baseline, path)
    entry = analyzed_entry(change, language, changed_ranges)
    return finalize_entry(entry, sg_info, repo, path, language, changed_ranges)
