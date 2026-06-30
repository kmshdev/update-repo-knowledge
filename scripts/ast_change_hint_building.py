"""Build structural hints from ast-grep matches."""

from __future__ import annotations

from pathlib import Path

from ast_change_config import KIND_PROFILES
from ast_change_match import ast_grep_matches, node_range, preview_text
from ast_change_paths import ranges_intersect


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
        collect_kind_hints(hints, seen, kind, matches, changed_ranges)
    hints.sort(key=lambda item: (item["range"]["end"] - item["range"]["start"], item["kind"]))
    return hints[:20], errors


def collect_kind_hints(
    hints: list[dict[str, object]],
    seen: set[tuple[str, int, int, str]],
    kind: str,
    matches: list[dict],
    changed_ranges: list[dict[str, int]],
) -> None:
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
