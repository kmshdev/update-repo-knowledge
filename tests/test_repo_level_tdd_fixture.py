from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "repo_level_tdd_fixture.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_level_tdd_fixture", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RepoLevelTddFixtureTests(unittest.TestCase):
    def test_uses_official_agentskills_repo_in_tmp(self) -> None:
        module = load_module()

        self.assertEqual(
            module.AGENTSKILLS_REPO_URL,
            "https://github.com/agentskills/agentskills.git",
        )
        self.assertEqual(module.DEFAULT_WORK_ROOT, Path("/tmp/update-repo-knowledge-tdd"))

    def test_refresh_refuses_to_delete_non_git_agentskills_dir(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            work_root = Path(tmp)
            repo = work_root / "agentskills"
            repo.mkdir()
            important = repo / "important.txt"
            important.write_text("keep\n", encoding="utf-8")

            with self.assertRaises(RuntimeError) as context:
                module.prepare_clone(work_root, refresh=True)

            self.assertIn("Refusing to refresh", str(context.exception))
            self.assertTrue(important.exists())

    def test_refresh_refuses_to_delete_symlink(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            work_root = Path(tmp)
            target = work_root / "real-agentskills"
            target.mkdir()
            repo = work_root / "agentskills"
            try:
                repo.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks are not available: {error}")

            with self.assertRaises(RuntimeError) as context:
                module.prepare_clone(work_root, refresh=True)

            self.assertIn("Refusing to refresh", str(context.exception))
            self.assertTrue(repo.is_symlink())

    def test_refresh_refuses_to_delete_worktree_style_git_file(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            work_root = Path(tmp)
            repo = work_root / "agentskills"
            repo.mkdir()
            git_file = repo / ".git"
            git_file.write_text("gitdir: /tmp/example-worktree\n", encoding="utf-8")

            with self.assertRaises(RuntimeError) as context:
                module.prepare_clone(work_root, refresh=True)

            self.assertIn("Refusing to refresh", str(context.exception))
            self.assertTrue(git_file.exists())

    def test_refresh_refuses_to_delete_non_official_git_checkout(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "agentskills"
            subprocess.run(["git", "init", str(repo)], check=True, stdout=subprocess.PIPE)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "add",
                    "origin",
                    "https://example.com/other.git",
                ],
                check=True,
            )
            marker = repo / "important.txt"
            marker.write_text("keep\n", encoding="utf-8")

            with self.assertRaises(RuntimeError) as context:
                module.remove_disposable_clone(repo)

            self.assertIn("Refusing to refresh", str(context.exception))
            self.assertTrue(marker.exists())

    def test_run_skill_script_preserves_non_json_stdout(self) -> None:
        module = load_module()

        def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                command,
                2,
                stdout="plain failure\n",
                stderr="bad json\n",
            )

        original_run = module.run
        module.run = fake_run
        try:
            result = module.run_skill_script(
                Path("/tmp/update-repo-knowledge/scripts/example.py"),
                [],
            )
        finally:
            module.run = original_run

        self.assertEqual(result["returncode"], 2)
        self.assertEqual(result["stdout"], {"raw": "plain failure"})
        self.assertEqual(result["stderr"], "bad json")

    def test_summarize_stops_after_failed_baseline(self) -> None:
        module = load_module()
        calls: list[str] = []

        def fake_run_skill_script(script: Path, args: list[str]) -> dict[str, object]:
            calls.append(script.name)
            return {
                "command": [script.name, *args],
                "returncode": 1,
                "stdout": {"error": "baseline failed"},
                "stderr": "baseline failed",
            }

        original_run_skill_script = module.run_skill_script
        module.run_skill_script = fake_run_skill_script
        try:
            result = module.summarize(
                Path("/tmp/update-repo-knowledge"),
                Path("/tmp/target-repo"),
            )
        finally:
            module.run_skill_script = original_run_skill_script

        self.assertEqual(calls, ["find_agents_baseline.py"])
        self.assertEqual(result["diff"], None)
        self.assertEqual(result["health"], None)

    def test_summarize_rejects_malformed_successful_baseline(self) -> None:
        module = load_module()
        calls: list[str] = []

        def fake_run_skill_script(script: Path, args: list[str]) -> dict[str, object]:
            calls.append(script.name)
            return {
                "command": [script.name, *args],
                "returncode": 0,
                "stdout": {"agent_files": {"path": "AGENTS.md"}},
                "stderr": "",
            }

        original_run_skill_script = module.run_skill_script
        module.run_skill_script = fake_run_skill_script
        try:
            with self.assertRaises(RuntimeError) as context:
                module.summarize(
                    Path("/tmp/update-repo-knowledge"),
                    Path("/tmp/target-repo"),
                )
        finally:
            module.run_skill_script = original_run_skill_script

        self.assertEqual(calls, ["find_agents_baseline.py"])
        self.assertIn("agent_files array", str(context.exception))
