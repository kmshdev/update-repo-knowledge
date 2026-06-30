"""Path and scope helpers for ast_change_hints.py."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ast_change_config import (
    LANGUAGE_BY_EXTENSION,
    LANGUAGE_BY_NAME,
    NO_DOC_PATH_PARTS,
    NO_DOC_SUFFIXES,
)


def language_for_path(path: str) -> Optional[str]:
    target = Path(path)
    name = target.name.lower()
    if name in LANGUAGE_BY_NAME:
        return LANGUAGE_BY_NAME[name]
    return LANGUAGE_BY_EXTENSION.get(target.suffix.lower())


def path_under_scope(path: str, scope: str) -> bool:
    return scope == "." or path == scope or path.startswith(f"{scope}/")


def nearest_agent(path: str, agents: list[dict[str, object]]) -> Optional[dict[str, object]]:
    candidates = [entry for entry in agents if path_under_scope(path, str(entry["scope"]))]
    if not candidates:
        return None
    return max(candidates, key=lambda entry: len(str(entry["scope"])))


def is_generated_or_binary(path: str) -> bool:
    target = Path(path)
    parts = set(target.parts)
    return target.suffix.lower() in NO_DOC_SUFFIXES or bool(parts.intersection(NO_DOC_PATH_PARTS))


def ranges_intersect(left: dict[str, int], right: dict[str, int]) -> bool:
    return left["start"] <= right["end"] and right["start"] <= left["end"]
