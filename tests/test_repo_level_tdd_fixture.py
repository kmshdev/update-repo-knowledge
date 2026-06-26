from __future__ import annotations

import importlib.util
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
