"""Emit adapter drift checks."""

from __future__ import annotations

from pathlib import Path

from check_knowledge_common import add_check, rel


def add_extra_content_check(
    repo: Path,
    checks: list[dict[str, str]],
    adapter: Path,
    adapter_name: str,
    nearest_label: str,
) -> None:
    add_check(
        checks,
        "adapter-extra-content",
        "warning",
        rel(repo, adapter),
        (
            f"{adapter_name} points to {nearest_label} but contains "
            "additional instruction content; keep adapters as short "
            "canonical pointers or declare this adapter canonical in "
            "AGENTS.md"
        ),
    )


def add_adapter_check(
    repo: Path,
    checks: list[dict[str, str]],
    adapter: Path,
    adapter_name: str,
    nearest_agents: Path | None,
    shape: str,
) -> None:
    nearest_label = rel(repo, nearest_agents) if nearest_agents else "nearest AGENTS.md"
    if shape == "extra-content":
        add_extra_content_check(repo, checks, adapter, adapter_name, nearest_label)
        return

    add_check(
        checks,
        "adapter-drift",
        "warning",
        rel(repo, adapter),
        f"{adapter_name} is not an adapter pointer to {nearest_label}",
    )
