"""Git, command, and JSON helpers for ast_change_hints.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ast_change_config import HUNK_PATTERN


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result


def run_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(args)} failed: {message}")
    return result


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def changed_ranges_from_diff(diff_text: str) -> list[dict[str, int]]:
    ranges: list[dict[str, int]] = []
    for line in diff_text.splitlines():
        match = HUNK_PATTERN.search(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        end = start if count == 0 else start + count - 1
        ranges.append({"start": start, "end": end})
    return ranges


def changed_ranges_for_path(repo: Path, baseline: str, path: str) -> list[dict[str, int]]:
    result = run_git(repo, ["diff", "--unified=0", baseline, "--", path])
    return changed_ranges_from_diff(result.stdout)
