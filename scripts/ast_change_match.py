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


def malformed_stream_error(
    command: list[str],
    file_path: Path,
    line_number: int,
    line: str,
    error: json.JSONDecodeError,
) -> str:
    snippet = line.strip()
    if len(snippet) > 120:
        snippet = f"{snippet[:117]}..."
    return (
        "Malformed ast-grep JSON stream output from "
        f"{' '.join(command)} for {file_path} at line {line_number}: "
        f"{error.msg}. Offending line: {snippet!r}. "
        "Rerun ast-grep with --json=stream or inspect ast-grep output."
    )


def ast_grep_matches(
    sg_path: str,
    file_path: Path,
    language: str,
    kind: str,
) -> tuple[list[dict], str]:
    command = [
        sg_path,
        "run",
        "-k",
        kind,
        "-l",
        language,
        "--json=stream",
        str(file_path),
    ]
    result = run_command(
        command,
        check=False,
    )
    if result.returncode != 0:
        return [], result.stderr.strip() or result.stdout.strip()

    matches = []
    for line_number, line in enumerate(result.stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            matches.append(json.loads(line))
        except json.JSONDecodeError as error:
            return [], malformed_stream_error(command, file_path, line_number, line, error)
    return matches, ""
