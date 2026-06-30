"""Adapter-file checks for repository knowledge stores."""

from __future__ import annotations

import os
from pathlib import Path

from check_knowledge_adapter_emit import add_adapter_check
from check_knowledge_adapter_shape import ADAPTER_FILES, adapter_shape
from check_knowledge_common import add_check


def nearest_agent_file(path: Path, agent_dirs: list[Path]) -> Path | None:
    candidates = [
        agent_dir
        for agent_dir in agent_dirs
        if path == agent_dir or agent_dir in path.parents
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: len(candidate.parts)) / "AGENTS.md"


def check_one_adapter(
    repo: Path,
    checks: list[dict[str, str]],
    adapter: Path,
    adapter_name: str,
    nearest_agents: Path | None,
) -> None:
    if adapter.is_symlink():
        return
    adapter_text = adapter.read_text(encoding="utf-8", errors="replace")
    shape = adapter_shape(adapter_text)
    if shape in {"short-pointer", "generated-pointer"}:
        return
    add_adapter_check(repo, checks, adapter, adapter_name, nearest_agents, shape)


def check_adapter_files(
    repo: Path,
    checks: list[dict[str, str]],
    base: Path,
    files: list[str],
    agent_dirs: list[Path],
) -> None:
    adapter_files = sorted(name for name in files if name in ADAPTER_FILES)
    if not adapter_files:
        return

    nearest_agents = nearest_agent_file(base, agent_dirs)
    for adapter_name in adapter_files:
        check_one_adapter(repo, checks, base / adapter_name, adapter_name, nearest_agents)


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
        check_adapter_files(repo, checks, base, files, agent_dirs)
