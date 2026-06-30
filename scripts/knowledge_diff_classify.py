"""Changed-file classification for knowledge_diff.py."""

from __future__ import annotations

from pathlib import Path

from knowledge_diff_config import NO_DOC_NAMES, NO_DOC_PATH_PARTS, NO_DOC_SUFFIXES


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
