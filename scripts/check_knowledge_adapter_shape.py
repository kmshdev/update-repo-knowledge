"""Classify adapter instruction files by structural shape."""

from __future__ import annotations

import re


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


def content_lines(lines: list[str]) -> list[str]:
    return [
        line for line in lines if not ADAPTER_DECORATIVE_LINE_PATTERN.search(line)
    ]


def is_short_pointer(stripped: str, lines: list[str]) -> bool:
    return (
        len(lines) <= ADAPTER_SHORT_POINTER_MAX_LINES
        and len(stripped) <= ADAPTER_SHORT_POINTER_MAX_CHARS
        and all(ADAPTER_POINTER_PATTERN.search(line) for line in content_lines(lines))
    )


def adapter_shape(adapter_text: str) -> str:
    stripped = adapter_text.strip()
    if not ADAPTER_POINTER_PATTERN.search(stripped):
        return "missing-pointer"

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    header = "\n".join(lines[:ADAPTER_GENERATED_HEADER_LINES])
    if ADAPTER_GENERATED_MARKER_PATTERN.search(header):
        return "generated-pointer"
    if is_short_pointer(stripped, lines):
        return "short-pointer"

    return "extra-content"
