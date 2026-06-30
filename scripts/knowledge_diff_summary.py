"""Summary assembly for knowledge_diff.py."""

from __future__ import annotations

from pathlib import Path

from knowledge_diff_classify import classify, nearest_agent
from knowledge_diff_git import changed_files


def baseline_agents(baseline_data: dict[str, object]) -> list[dict[str, object]]:
    return [
        entry
        for entry in baseline_data.get("agent_files", [])
        if isinstance(entry, dict) and entry.get("last_commit")
    ]


def no_baseline_result(repo: Path) -> dict[str, object]:
    return {
        "repo": str(repo),
        "baseline": None,
        "changes": [],
        "summary": {"changed_files": 0, "review_required": 0, "no_doc_impact": 0},
        "warnings": ["No tracked AGENTS.md baseline commit found; initial setup is required."],
    }


def change_entry(
    path: str,
    status: str,
    owner: dict[str, object],
) -> dict[str, object]:
    impact, reason = classify(path, status)
    return {
        "path": path,
        "status": status,
        "agent_file": owner["path"],
        "doc_impact": impact,
        "reason": reason,
    }


def collect_changes(repo: Path, agents: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    all_changes: dict[str, dict[str, object]] = {}
    for entry in agents:
        baseline = str(entry["last_commit"])
        scope = str(entry["scope"])
        for status, path in changed_files(repo, baseline, scope):
            owner = nearest_agent(path, agents) or entry
            if owner is not entry:
                continue
            all_changes[path] = change_entry(path, status, owner)
    return all_changes


def summarize_counts(changes: list[dict[str, object]]) -> dict[str, int]:
    review_required = sum(
        1 for item in changes if item["doc_impact"] in {"review", "uncertain"}
    )
    no_doc_impact = sum(1 for item in changes if item["doc_impact"] == "no-doc-impact")
    return {
        "changed_files": len(changes),
        "review_required": review_required,
        "no_doc_impact": no_doc_impact,
    }


def summarize(repo: Path, baseline_data: dict[str, object]) -> dict[str, object]:
    agents = baseline_agents(baseline_data)
    if not agents:
        return no_baseline_result(repo)

    all_changes = collect_changes(repo, agents)
    changes = [all_changes[path] for path in sorted(all_changes)]
    baselines = sorted({str(entry["last_commit"]) for entry in agents})
    return {
        "repo": str(repo),
        "baseline": baselines[0] if len(baselines) == 1 else None,
        "changes": changes,
        "summary": summarize_counts(changes),
    }
