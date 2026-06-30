"""Summary assembly for ast_change_hints.py."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ast_change_analysis import analyze_change
from ast_change_match import find_sg


def empty_summary() -> dict[str, int]:
    return {
        "eligible_files": 0,
        "analyzed_files": 0,
        "unsupported_files": 0,
        "skipped_files": 0,
    }


def record_analysis_state(summary: dict[str, int], state: str) -> None:
    if state == "eligible":
        summary["eligible_files"] += 1
        return
    if state == "analyzed":
        summary["eligible_files"] += 1
        summary["analyzed_files"] += 1
        return
    if state == "unsupported":
        summary["unsupported_files"] += 1
        return
    summary["skipped_files"] += 1


def baseline_agents(baseline_data: dict[str, object]) -> list[dict[str, object]]:
    return [
        entry
        for entry in baseline_data.get("agent_files", [])
        if isinstance(entry, dict) and entry.get("last_commit")
    ]


def iter_change_objects(diff_data: dict[str, object]) -> list[dict[str, object]]:
    return [
        change
        for change in diff_data.get("changes", [])
        if isinstance(change, dict)
    ]


def summarize(
    repo: Path,
    baseline_data: dict[str, object],
    diff_data: dict[str, object],
    sg_path: Optional[str] = None,
) -> dict[str, object]:
    agents = baseline_agents(baseline_data)
    sg_info = find_sg(sg_path)
    changes = []
    summary = empty_summary()

    for change in iter_change_objects(diff_data):
        entry, state = analyze_change(repo, change, agents, sg_info)
        changes.append(entry)
        record_analysis_state(summary, state)

    return {"repo": str(repo), "sg": sg_info, "summary": summary, "changes": changes}
