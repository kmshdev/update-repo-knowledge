from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "ast_change_hints.py"
CONFIG_PATH = SKILL_DIR / "scripts" / "ast_change_config.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ast_change_hints", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config_module():
    spec = importlib.util.spec_from_file_location("ast_change_config", CONFIG_PATH)
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


class TempGitRepo(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def baseline_json(self) -> dict[str, object]:
        return {
            "repo": str(self.repo),
            "agent_files": [
                {
                    "path": "AGENTS.md",
                    "scope": ".",
                    "last_commit": self.baseline,
                    "exists": True,
                    "tracked": True,
                }
            ],
        }

    def diff_json(self, path: str, doc_impact: str = "review") -> dict[str, object]:
        return {
            "repo": str(self.repo),
            "changes": [
                {
                    "path": path,
                    "status": "M",
                    "agent_file": "AGENTS.md",
                    "doc_impact": doc_impact,
                    "reason": "source or project file changed under covered scope",
                }
            ],
            "summary": {"changed_files": 1, "review_required": 1, "no_doc_impact": 0},
        }


class LanguageMappingTests(unittest.TestCase):
    def test_maps_broad_ast_grep_languages(self) -> None:
        module = load_module()
        examples = {
            "tool.sh": "bash",
            "module.c": "c",
            "module.cpp": "cpp",
            "Service.cs": "csharp",
            "site.css": "css",
            "app.ex": "elixir",
            "main.go": "go",
            "Lib.hs": "haskell",
            "page.html": "html",
            "Service.java": "java",
            "app.js": "javascript",
            "package.json": "json",
            "Screen.kt": "kotlin",
            "plugin.lua": "lua",
            "index.php": "php",
            "worker.py": "python",
            "job.rb": "ruby",
            "lib.rs": "rust",
            "Job.scala": "scala",
            "View.swift": "swift",
            "client.ts": "typescript",
            "View.tsx": "tsx",
            "config.yaml": "yaml",
        }

        for filename, expected in examples.items():
            with self.subTest(filename=filename):
                self.assertEqual(module.language_for_path(filename), expected)

    def test_haskell_profile_uses_tree_sitter_type_alias(self) -> None:
        config = load_config_module()

        self.assertIn("type_alias", config.KIND_PROFILES["haskell"])
        self.assertNotIn("type_synomym", config.KIND_PROFILES["haskell"])


class DiffParsingTests(unittest.TestCase):
    def test_parses_add_modify_delete_and_multi_hunk_ranges(self) -> None:
        module = load_module()
        diff_text = "\n".join(
            [
                "@@ -1,2 +1,3 @@",
                " line",
                "-old",
                "+new",
                "+added",
                "@@ -10,2 +11,0 @@",
                "-removed",
                "-removed too",
                "@@ -20 +20,2 @@",
                "-before",
                "+after",
                "+again",
            ]
        )

        self.assertEqual(
            module.changed_ranges_from_diff(diff_text),
            [
                {"start": 1, "end": 3},
                {"start": 11, "end": 11},
                {"start": 20, "end": 21},
            ],
        )


class SummaryAccountingTests(unittest.TestCase):
    def test_record_analysis_state_counts_each_state(self) -> None:
        module = load_module()
        summary = module.empty_summary()

        module.record_analysis_state(summary, "eligible")
        module.record_analysis_state(summary, "analyzed")
        module.record_analysis_state(summary, "unsupported")
        module.record_analysis_state(summary, "skipped")
        module.record_analysis_state(summary, "ignored-state")

        self.assertEqual(
            summary,
            {
                "eligible_files": 2,
                "analyzed_files": 1,
                "unsupported_files": 1,
                "skipped_files": 2,
            },
        )

    def test_summarize_uses_summary_accounting_helper(self) -> None:
        module = load_module()
        original_analyze_change = module.analyze_change

        states = iter(["eligible", "analyzed", "unsupported", "skipped"])

        def fake_analyze_change(repo, change, agents, sg_info):
            state = next(states)
            entry = module.base_change(change)
            entry["ast_status"] = state
            return entry, state

        module.analyze_change = fake_analyze_change
        try:
            result = module.summarize(
                Path("/tmp/example-repo"),
                {
                    "agent_files": [
                        {
                            "path": "AGENTS.md",
                            "scope": ".",
                            "last_commit": "abc123",
                            "exists": True,
                            "tracked": True,
                        }
                    ]
                },
                {
                    "changes": [
                        {
                            "path": "one.py",
                            "status": "M",
                            "agent_file": "AGENTS.md",
                            "doc_impact": "review",
                        },
                        {
                            "path": "two.py",
                            "status": "M",
                            "agent_file": "AGENTS.md",
                            "doc_impact": "review",
                        },
                        {
                            "path": "three.txt",
                            "status": "M",
                            "agent_file": "AGENTS.md",
                            "doc_impact": "review",
                        },
                        {
                            "path": "four.lock",
                            "status": "M",
                            "agent_file": "AGENTS.md",
                            "doc_impact": "no-doc-impact",
                        },
                    ]
                },
                sg_path="/not/a/real/sg",
            )
        finally:
            module.analyze_change = original_analyze_change

        self.assertEqual(
            result["summary"],
            {
                "eligible_files": 2,
                "analyzed_files": 1,
                "unsupported_files": 1,
                "skipped_files": 1,
            },
        )
        self.assertEqual(
            [change["path"] for change in result["changes"]],
            ["one.py", "two.py", "three.txt", "four.lock"],
        )


class MissingAstGrepTests(TempGitRepo):
    def test_missing_sg_returns_advisory_entries_without_failure(self) -> None:
        module = load_module()
        write(
            self.repo / "src" / "service.py",
            "def load_config(path):\n    return {'path': path}\n",
        )
        run(["git", "add", "src/service.py"], self.repo)
        run(["git", "commit", "-m", "Add service"], self.repo)
        write(
            self.repo / "src" / "service.py",
            "def load_config(path):\n    return {'path': path, 'ok': True}\n",
        )

        result = module.summarize(
            self.repo,
            self.baseline_json(),
            self.diff_json("src/service.py"),
            sg_path="/not/a/real/sg",
        )

        self.assertFalse(result["sg"]["available"])
        self.assertEqual(result["changes"][0]["ast_status"], "sg-missing")
        self.assertEqual(result["changes"][0]["language"], "python")
        self.assertEqual(result["changes"][0]["hints"], [])
        self.assertEqual(result["summary"]["eligible_files"], 1)
        self.assertEqual(result["summary"]["analyzed_files"], 0)


@unittest.skipUnless(shutil.which("sg"), "ast-grep CLI is not installed")
class AstGrepIntegrationTests(TempGitRepo):
    def test_python_change_reports_enclosing_function_hint(self) -> None:
        module = load_module()
        write(
            self.repo / "src" / "service.py",
            "\n".join(
                [
                    "def load_config(path):",
                    "    value = {'path': path}",
                    "    return value",
                    "",
                ]
            ),
        )
        run(["git", "add", "src/service.py"], self.repo)
        run(["git", "commit", "-m", "Add service"], self.repo)
        write(
            self.repo / "src" / "service.py",
            "\n".join(
                [
                    "def load_config(path):",
                    "    value = {'path': path, 'ok': True}",
                    "    return value",
                    "",
                ]
            ),
        )

        result = module.summarize(self.repo, self.baseline_json(), self.diff_json("src/service.py"))

        self.assertEqual(result["sg"]["available"], True)
        self.assertEqual(result["changes"][0]["ast_status"], "ok")
        self.assertEqual(result["changes"][0]["hints"][0]["kind"], "function_definition")
        self.assertIn("def load_config", result["changes"][0]["hints"][0]["preview"])

    def test_no_doc_impact_files_are_skipped(self) -> None:
        module = load_module()
        write(self.repo / "package-lock.json", "{}\n")
        result = module.summarize(
            self.repo,
            self.baseline_json(),
            self.diff_json("package-lock.json", doc_impact="no-doc-impact"),
        )

        self.assertEqual(result["changes"][0]["ast_status"], "not-review-required")
        self.assertEqual(result["summary"]["skipped_files"], 1)

    def test_smoke_supported_languages_do_not_crash(self) -> None:
        module = load_module()
        samples = {
            "script.sh": ("bash", "greet() {\n  echo hello\n}\n"),
            "module.c": ("c", "int greet(void) {\n  return 1;\n}\n"),
            "module.cpp": ("cpp", "int greet() {\n  return 1;\n}\n"),
            "Service.cs": ("csharp", "class Service {\n  string Greet() { return \"hi\"; }\n}\n"),
            "site.css": ("css", ".greeting {\n  color: red;\n}\n"),
            "app.ex": ("elixir", "defmodule App do\n  def greet, do: \"hi\"\nend\n"),
            "main.go": ("go", "package main\nfunc greet() string { return \"hi\" }\n"),
            "Lib.hs": ("haskell", "greet = \"hi\"\n"),
            "page.html": ("html", "<main>\n  <h1>hi</h1>\n</main>\n"),
            "Service.java": (
                "java",
                "class Service {\n  String greet() { return \"hi\"; }\n}\n",
            ),
            "app.js": ("javascript", "function greet() { return 'hi'; }\n"),
            "Screen.kt": ("kotlin", "class Screen {\n  fun greet() = \"hi\"\n}\n"),
            "plugin.lua": ("lua", "function greet()\n  return \"hi\"\nend\n"),
            "index.php": ("php", "<?php\nfunction greet() { return \"hi\"; }\n"),
            "job.rb": ("ruby", "def greet\n  \"hi\"\nend\n"),
            "lib.rs": ("rust", "fn greet() -> &'static str {\n  \"hi\"\n}\n"),
            "Job.scala": ("scala", "object Job {\n  def greet = \"hi\"\n}\n"),
            "View.swift": ("swift", "func greet() -> String {\n  return \"hi\"\n}\n"),
            "client.ts": ("typescript", "export function greet() { return 'hi' }\n"),
            "View.tsx": ("tsx", "export function View() { return <div /> }\n"),
            "config.json": ("json", "{\"name\": \"old\"}\n"),
            "config.yaml": ("yaml", "name: old\n"),
        }

        for filename, (_language, initial_text) in samples.items():
            with self.subTest(filename=filename):
                write(self.repo / filename, initial_text)
                run(["git", "add", filename], self.repo)
                run(["git", "commit", "-m", f"Add {filename}"], self.repo)
                changed_text = initial_text.replace("old", "new").replace("hi", "hello")
                write(self.repo / filename, changed_text)
                result = module.summarize(self.repo, self.baseline_json(), self.diff_json(filename))
                self.assertIn(
                    result["changes"][0]["ast_status"],
                    {"ok", "parsed-no-hints", "ast-grep-error"},
                )
                run(["git", "checkout", "--", filename], self.repo)


if __name__ == "__main__":
    sys.exit(unittest.main())
