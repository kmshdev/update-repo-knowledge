"""Markdown link checks for repository knowledge stores."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from check_knowledge_common import add_check, rel


LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


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


def local_link_target(repo: Path, path: Path, raw_target: str) -> Path | None:
    if not raw_target or is_external_link(raw_target):
        return None
    clean_target = raw_target.split("#", 1)[0].strip()
    if not clean_target:
        return None
    target_path = (path.parent / unquote(clean_target)).resolve()
    try:
        target_path.relative_to(repo)
    except ValueError:
        return None
    return target_path


def target_exists(target_path: Path) -> bool:
    if target_path.is_dir():
        return (target_path / "index.md").exists()
    return target_path.exists()


def check_markdown_links(repo: Path, checks: list[dict[str, str]]) -> None:
    for path in markdown_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LINK_PATTERN.finditer(text):
            raw_target = match.group(1).strip()
            target_path = local_link_target(repo, path, raw_target)
            if not target_path or target_exists(target_path):
                continue
            clean_target = raw_target.split("#", 1)[0].strip()
            add_check(
                checks,
                "broken-markdown-link",
                "error",
                rel(repo, path),
                f"Link target {clean_target} does not exist",
            )
