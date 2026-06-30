"""ast-grep process and match helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from ast_change_io import run_command


def find_sg(sg_path: Optional[str]) -> dict[str, object]:
    path = sg_path or shutil.which("sg")
    if not path or not Path(path).exists():
        return {"available": False, "path": path, "version": None}
    result = run_command([path, "--version"], check=False)
    if result.returncode != 0:
        return {"available": False, "path": path, "version": None}
    return {"available": True, "path": path, "version": result.stdout.strip()}


def node_range(match: dict[str, object]) -> dict[str, int]:
    raw_range = match.get("range")
    if not isinstance(raw_range, dict):
        return {"start": 0, "end": 0}
    start = raw_range.get("start")
    end = raw_range.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return {"start": 0, "end": 0}
    return {"start": int(start.get("line", 0)) + 1, "end": int(end.get("line", 0)) + 1}


def preview_text(match: dict[str, object]) -> str:
    text = str(match.get("text") or match.get("lines") or "")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return ""


def ast_grep_matches(
    sg_path: str,
    file_path: Path,
    language: str,
    kind: str,
) -> tuple[list[dict], str]:
    result = run_command(
        [
            sg_path,
            "run",
            "-k",
            kind,
            "-l",
            language,
            "--json=stream",
            str(file_path),
        ],
        check=False,
    )
    if result.returncode != 0:
        return [], result.stderr.strip() or result.stdout.strip()

    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        matches.append(json.loads(line))
    return matches, ""
