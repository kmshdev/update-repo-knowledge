#!/usr/bin/env python3
"""Run repo-level TDD diagnostics against a disposable agentskills clone."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


AGENTSKILLS_REPO_URL = "https://github.com/agentskills/agentskills.git"
DEFAULT_WORK_ROOT = Path("/tmp/update-repo-knowledge-tdd")
DISPOSABLE_SENTINEL = ".update-repo-knowledge-disposable"


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command and return captured text output."""
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def require_success(result: subprocess.CompletedProcess[str], action: str) -> None:
    """Raise an actionable error when a subprocess fails."""
    if result.returncode == 0:
        return
    output = result.stderr.strip() or result.stdout.strip()
    raise RuntimeError(f"{action} failed with exit {result.returncode}: {output}")


def prepare_clone(work_root: Path, refresh: bool) -> Path:
    """Clone the official agentskills repo into the disposable work root."""
    repo = work_root / "agentskills"
    if refresh and repo.exists():
        remove_disposable_clone(repo)

    work_root.mkdir(parents=True, exist_ok=True)
    if repo.exists():
        require_success(run(["git", "fetch", "--all", "--prune"], repo), "git fetch")
        require_success(run(["git", "checkout", "main"], repo), "git checkout main")
        require_success(run(["git", "reset", "--hard", "origin/main"], repo), "git reset")
        return repo

    require_success(
        run(["git", "clone", AGENTSKILLS_REPO_URL, str(repo)]),
        f"git clone {AGENTSKILLS_REPO_URL}",
    )
    mark_disposable_clone(repo)
    return repo


def mark_disposable_clone(repo: Path) -> None:
    """Mark a freshly created fixture clone as safe for future refresh."""
    (repo / DISPOSABLE_SENTINEL).write_text(
        "Created by repo_level_tdd_fixture.py for disposable validation.\n",
        encoding="utf-8",
    )


def is_default_fixture_clone(repo: Path) -> bool:
    """Return whether repo is the historical default disposable fixture path."""
    try:
        return repo.resolve() == (DEFAULT_WORK_ROOT / "agentskills").resolve()
    except OSError:
        return False


def remove_disposable_clone(repo: Path) -> None:
    """Remove an existing checkout only when it is clearly disposable."""
    git_dir = repo / ".git"
    remote = run(["git", "config", "--get", "remote.origin.url"], repo)
    remote_url = remote.stdout.strip()
    has_disposable_signal = (repo / DISPOSABLE_SENTINEL).is_file() or is_default_fixture_clone(repo)
    if (
        repo.is_symlink()
        or not repo.is_dir()
        or not git_dir.is_dir()
        or remote.returncode != 0
        or remote_url != AGENTSKILLS_REPO_URL
        or not has_disposable_signal
    ):
        raise RuntimeError(
            "Refusing to refresh non-disposable agentskills path: "
            f"{repo}. Delete it manually or choose a different --work-root."
        )
    shutil.rmtree(repo)


def parse_stdout_payload(stdout: str) -> dict[str, object]:
    """Parse JSON stdout while preserving plain-text failures."""
    text = stdout.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def run_skill_script(script: Path, args: list[str]) -> dict[str, object]:
    """Run one skill script and return its JSON or captured failure."""
    result = run(["uv", "run", "--script", str(script), *args], script.parents[1])
    payload = parse_stdout_payload(result.stdout)
    return {
        "command": ["uv", "run", "--script", str(script), *args],
        "returncode": result.returncode,
        "stdout": payload,
        "stderr": result.stderr.strip(),
    }


def require_baseline_payload(baseline: dict[str, object]) -> dict[str, object]:
    """Return valid baseline stdout or raise an actionable fixture error."""
    payload = baseline.get("stdout")
    if not isinstance(payload, dict) or not isinstance(payload.get("agent_files"), list):
        raise RuntimeError(
            "find_agents_baseline.py returned malformed JSON: "
            "stdout must contain an agent_files array"
        )
    return payload


def summarize(skill_dir: Path, target_repo: Path) -> dict[str, object]:
    """Run baseline, diff, and health diagnostics against target_repo."""
    baseline_script = skill_dir / "scripts" / "find_agents_baseline.py"
    diff_script = skill_dir / "scripts" / "knowledge_diff.py"
    check_script = skill_dir / "scripts" / "check_knowledge_store.py"

    baseline = run_skill_script(baseline_script, [str(target_repo), "--json"])
    if baseline["returncode"] != 0:
        return {
            "target_repo": str(target_repo),
            "baseline": baseline,
            "diff": None,
            "health": None,
        }

    baseline_json = json.dumps(require_baseline_payload(baseline))
    baseline_path = target_repo.parent / "baseline.json"
    baseline_path.write_text(baseline_json, encoding="utf-8")

    diff = run_skill_script(
        diff_script,
        [str(target_repo), "--baseline-json", str(baseline_path), "--json"],
    )
    health = run_skill_script(check_script, [str(target_repo), "--json"])
    return {
        "target_repo": str(target_repo),
        "baseline": baseline,
        "diff": diff,
        "health": health,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-root",
        default=str(DEFAULT_WORK_ROOT),
        help="Disposable directory used for the agentskills clone",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Delete and reclone the disposable agentskills checkout first",
    )
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    try:
        target_repo = prepare_clone(Path(args.work_root).expanduser(), args.refresh)
        result = summarize(skill_dir, target_repo)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
