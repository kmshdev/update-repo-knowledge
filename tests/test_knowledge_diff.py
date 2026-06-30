from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"


def load_script_module(name: str):
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class KnowledgeDiffGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(["git", "init"], self.repo)
        run(["git", "config", "user.email", "test@example.com"], self.repo)
        run(["git", "config", "user.name", "Test User"], self.repo)
        write(self.repo / "AGENTS.md", "# Test Repo\n")
        run(["git", "add", "AGENTS.md"], self.repo)
        run(["git", "commit", "-m", "Add agents"], self.repo)
        self.baseline = run(["git", "rev-parse", "HEAD"], self.repo).stdout.strip()
        self.module = load_script_module("knowledge_diff_git")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_baseline_rejects_non_array_agent_files(self) -> None:
        baseline_path = self.repo / "baseline.json"
        baseline_path.write_text(
            json.dumps({"agent_files": {"path": "AGENTS.md"}}),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            self.module.load_baseline(baseline_path)

    def test_changed_files_includes_untracked_files_under_scope(self) -> None:
        write(self.repo / "packages" / "api" / "service.py", "print('api')\n")
        write(self.repo / "packages" / "web" / "app.py", "print('web')\n")

        changes = self.module.changed_files(self.repo, self.baseline, "packages/api")

        self.assertEqual(changes, [("??", "packages/api/service.py")])


class KnowledgeDiffSummaryTests(unittest.TestCase):
    def test_collect_changes_skips_paths_owned_by_deeper_agent_scope(self) -> None:
        module = load_script_module("knowledge_diff_summary")
        agents = [
            {"path": "AGENTS.md", "scope": ".", "last_commit": "root"},
            {
                "path": "packages/api/AGENTS.md",
                "scope": "packages/api",
                "last_commit": "nested",
            },
        ]
        calls: list[str] = []

        def fake_changed_files(repo: Path, baseline: str, scope: str):
            calls.append(scope)
            if scope == ".":
                return [("M", "packages/api/service.py")]
            return []

        original_changed_files = module.changed_files
        module.changed_files = fake_changed_files
        try:
            changes = module.collect_changes(Path("/tmp/repo"), agents)
        finally:
            module.changed_files = original_changed_files

        self.assertEqual(calls, [".", "packages/api"])
        self.assertEqual(changes, {})
