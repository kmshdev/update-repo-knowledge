from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "check_knowledge_store.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_knowledge_store", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def adapter_checks(result: dict[str, object]) -> list[dict[str, str]]:
    checks = result["checks"]
    assert isinstance(checks, list)
    return [
        check
        for check in checks
        if isinstance(check, dict) and str(check.get("id", "")).startswith("adapter-")
    ]


def checks_by_id(result: dict[str, object], check_id: str) -> list[dict[str, str]]:
    checks = result["checks"]
    assert isinstance(checks, list)
    return [
        check
        for check in checks
        if isinstance(check, dict) and check.get("id") == check_id
    ]


class CheckKnowledgeStoreAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        write(self.repo / "AGENTS.md", "# Test Repo\n\nCanonical instructions.\n")
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def validate(self) -> dict[str, object]:
        return self.module.validate(self.repo)

    def test_short_pointer_adapter_passes(self) -> None:
        write(
            self.repo / "CLAUDE.md",
            "Canonical repository instructions live in AGENTS.md.\n",
        )

        result = self.validate()

        self.assertEqual(adapter_checks(result), [])

    def test_symlink_adapter_passes(self) -> None:
        try:
            (self.repo / "CLAUDE.md").symlink_to(self.repo / "AGENTS.md")
        except OSError as error:
            self.skipTest(f"symlinks are not available: {error}")

        result = self.validate()

        self.assertEqual(adapter_checks(result), [])

    def test_generated_adapter_with_source_marker_passes(self) -> None:
        write(
            self.repo / "CLAUDE.md",
            "\n".join(
                [
                    "<!-- Generated from AGENTS.md. Do not edit directly. -->",
                    "",
                    "# Claude Adapter",
                    "",
                    "Canonical instructions live in AGENTS.md.",
                    "",
                    "This file is generated for tool compatibility.",
                    "",
                ]
            ),
        )

        result = self.validate()

        self.assertEqual(adapter_checks(result), [])

    def test_manual_adapter_without_pointer_warns(self) -> None:
        write(
            self.repo / "CLAUDE.md",
            "\n".join(
                [
                    "# Claude Instructions",
                    "",
                    "Run npm test before editing docs.",
                    "",
                ]
            ),
        )

        result = self.validate()
        checks = adapter_checks(result)

        self.assertEqual([check["id"] for check in checks], ["adapter-drift"])
        self.assertIn("is not an adapter pointer", checks[0]["message"])

    def test_pointer_with_extra_instruction_content_warns(self) -> None:
        write(
            self.repo / "CLAUDE.md",
            "\n".join(
                [
                    "# Claude Instructions",
                    "",
                    "Canonical repository instructions live in AGENTS.md.",
                    "",
                    "Always run npm test before updating repository knowledge.",
                    "The product architecture is documented only in this file.",
                    "",
                ]
            ),
        )

        result = self.validate()
        checks = adapter_checks(result)

        self.assertEqual([check["id"] for check in checks], ["adapter-extra-content"])
        self.assertIn("points to AGENTS.md", checks[0]["message"])
        self.assertIn("additional instruction content", checks[0]["message"])

    def test_nested_agent_scope_uses_nearest_agents_file(self) -> None:
        write(self.repo / "packages" / "api" / "AGENTS.md", "# API Agents\n")
        write(
            self.repo / "packages" / "api" / "CLAUDE.md",
            "\n".join(
                [
                    "# API Claude Instructions",
                    "",
                    "Canonical repository instructions live in AGENTS.md.",
                    "",
                    "Use pnpm test --filter api before changing API docs.",
                    "API routing facts live here.",
                    "",
                ]
            ),
        )

        result = self.validate()
        checks = adapter_checks(result)

        self.assertEqual([check["id"] for check in checks], ["adapter-extra-content"])
        self.assertEqual(checks[0]["path"], "packages/api/CLAUDE.md")
        self.assertIn("packages/api/AGENTS.md", checks[0]["message"])


class CheckKnowledgeStoreStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.module = load_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def validate(self) -> dict[str, object]:
        return self.module.validate(self.repo)

    def test_missing_root_agents_is_error(self) -> None:
        result = self.validate()
        checks = checks_by_id(result, "missing-root-agents")

        self.assertEqual(result["summary"]["errors"], 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["severity"], "error")
        self.assertEqual(checks[0]["path"], "AGENTS.md")

    def test_docs_directory_without_index_is_warning(self) -> None:
        write(self.repo / "AGENTS.md", "# Test Repo\n")
        write(self.repo / "docs" / "api.md", "# API\n")

        result = self.validate()
        checks = checks_by_id(result, "missing-docs-index")

        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(result["summary"]["warnings"], 1)
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["severity"], "warning")
        self.assertEqual(checks[0]["path"], "docs")
