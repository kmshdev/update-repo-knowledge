# Adapter Drift Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Warn when a tool-specific adapter points to `AGENTS.md` but also carries substantial extra instruction content.

**Architecture:** Keep adapter detection structural and deterministic inside `scripts/check_knowledge_store.py`. Add standard-library tests that exercise valid adapter shapes and drift cases without touching `knowledge_diff.py`, `ast_change_hints.py`, or documentation-generation behavior.

**Tech Stack:** Python standard library, `unittest`, temporary directories, existing skill validation script, `uv run --script` conventions.

---

## Scope Check

This plan covers one subsystem: adapter-shape validation in
`check_knowledge_store.py` plus the minimal skill documentation needed to avoid
overclaiming capability. It does not include semantic equivalence checking,
AST-based analysis, runtime checks, or documentation generation.

## File Structure

- Modify `scripts/check_knowledge_store.py`
  - Add deterministic adapter-shape constants and `adapter_shape()`.
  - Preserve existing JSON output shape: checks are still dictionaries with
    `id`, `severity`, `path`, and `message`.
  - Add only one new warning id: `adapter-extra-content`.
- Create `tests/test_check_knowledge_store.py`
  - Load the script module directly, matching the existing test style.
  - Use `tempfile.TemporaryDirectory()` and plain files.
  - Test behavior through `validate(repo)`, not private implementation details.
- Modify `references/intent-layer-capture.md`
  - Document the structural adapter boundary and the lack of semantic guarantee.
- Modify `SKILL.md`
  - Add one concise adapter-shape sentence only.

## Task 1: Add Adapter Drift Tests And Script Behavior

**Files:**
- Create: `tests/test_check_knowledge_store.py`
- Modify: `scripts/check_knowledge_store.py`

- [ ] **Step 1: Write the failing adapter tests**

Create `tests/test_check_knowledge_store.py`:

```python
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
```

- [ ] **Step 2: Run the targeted failing test**

Run:

```bash
cd <repo-root>
uv run python -m unittest \
  tests.test_check_knowledge_store.CheckKnowledgeStoreAdapterTests.test_pointer_with_extra_instruction_content_warns \
  -v
```

Expected: FAIL because current `check_knowledge_store.py` accepts any adapter
containing `AGENTS.md` and emits no `adapter-extra-content` warning.

- [ ] **Step 3: Add deterministic adapter-shape helpers**

In `scripts/check_knowledge_store.py`,
add these constants after `ADAPTER_POINTER_PATTERN`:

```python
ADAPTER_GENERATED_HEADER_LINES = 10
ADAPTER_SHORT_POINTER_MAX_CHARS = 500
ADAPTER_SHORT_POINTER_MAX_LINES = 5
ADAPTER_GENERATED_MARKER_PATTERN = re.compile(
    r"\b(auto[- ]?generated|generated from|generated by|do not edit)\b",
    re.IGNORECASE,
)
```

Add this function after `rel()`:

```python
def adapter_shape(adapter_text: str) -> str:
    stripped = adapter_text.strip()
    if not ADAPTER_POINTER_PATTERN.search(stripped):
        return "missing-pointer"

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    header = "\n".join(lines[:ADAPTER_GENERATED_HEADER_LINES])
    if ADAPTER_GENERATED_MARKER_PATTERN.search(header):
        return "generated-pointer"

    if (
        len(lines) <= ADAPTER_SHORT_POINTER_MAX_LINES
        and len(stripped) <= ADAPTER_SHORT_POINTER_MAX_CHARS
        and lines
        and all(ADAPTER_POINTER_PATTERN.search(line) for line in lines)
    ):
        return "short-pointer"

    return "extra-content"
```

- [ ] **Step 4: Replace the adapter warning branch**

In `check_agent_files()`, replace this block:

```python
            adapter_text = adapter.read_text(encoding="utf-8", errors="replace").strip()
            if ADAPTER_POINTER_PATTERN.search(adapter_text):
                continue
            nearest_label = rel(repo, nearest_agents) if nearest_agents else "nearest AGENTS.md"
            add_check(
                checks,
                "adapter-drift",
                "warning",
                rel(repo, adapter),
                f"{adapter_name} is not an adapter pointer to {nearest_label}",
            )
```

With this block:

```python
            adapter_text = adapter.read_text(encoding="utf-8", errors="replace")
            shape = adapter_shape(adapter_text)
            if shape in {"short-pointer", "generated-pointer"}:
                continue

            nearest_label = rel(repo, nearest_agents) if nearest_agents else "nearest AGENTS.md"
            if shape == "extra-content":
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
                continue

            add_check(
                checks,
                "adapter-drift",
                "warning",
                rel(repo, adapter),
                f"{adapter_name} is not an adapter pointer to {nearest_label}",
            )
```

- [ ] **Step 5: Run the adapter test file**

Run:

```bash
cd <repo-root>
uv run python -m unittest tests.test_check_knowledge_store -v
```

Expected: PASS. The output should include six passing tests and no warnings from
the Python runtime.

- [ ] **Step 6: Run the full test suite**

Run:

```bash
cd <repo-root>
uv run python -m unittest discover -s tests
```

Expected: PASS. AST integration tests may be skipped when `sg` is unavailable;
that is acceptable because those tests already declare the skip condition.

- [ ] **Step 7: Commit the tested script behavior**

Run:

```bash
cd <repo-root>
git add scripts/check_knowledge_store.py tests/test_check_knowledge_store.py
git commit -m "Warn on adapter pointers with extra instructions"
```

Expected: commit succeeds with only the script and new test file staged.

## Task 2: Document The Structural Adapter Boundary

**Files:**
- Modify: `references/intent-layer-capture.md`
- Modify: `SKILL.md`

- [ ] **Step 1: Update the adapter policy reference**

In `references/intent-layer-capture.md`,
replace the `## Adapter Policy` section with:

```markdown
## Adapter Policy

Treat non-`AGENTS.md` instruction files as adapters unless the repository says
otherwise.

Adapter checks are structural. Passing adapter checks means the adapter has an
accepted shape; it does not prove two instruction files are semantically
equivalent.

Valid adapter patterns:

- Symlink to `AGENTS.md`.
- Short file that says canonical instructions live in `AGENTS.md`.
- Generated file with a clear generated provenance marker.

Invalid patterns:

- Manual copy of the same instructions.
- Conflicting commands in `AGENTS.md` and `CLAUDE.md`.
- Tool-specific file that silently adds product or architecture facts.
- Pointer file that also contains product facts, architecture facts, commands,
  or policy instructions unless the repository declares that adapter canonical.
```

- [ ] **Step 2: Add one concise SKILL.md sentence**

In `SKILL.md`, under
`## Evidence Rules`, replace this bullet:

```markdown
- In this skill, treat `CLAUDE.md`, Cursor rules, and other tool-specific
  instruction files as adapters unless the repository explicitly says they are
  canonical.
```

With:

```markdown
- In this skill, treat `CLAUDE.md`, Cursor rules, and other tool-specific
  instruction files as adapters unless the repository explicitly says they are
  canonical. Adapters should be symlinks, generated files with a generated
  provenance marker, or short pointers to `AGENTS.md`; substantial extra
  instructions in adapters are drift.
```

- [ ] **Step 3: Run markdown link and skill health checks**

Run:

```bash
cd <repo-root>
uv run python scripts/check_knowledge_store.py . --json
```

Expected: JSON output with `"errors": 0`. Existing warnings are acceptable only
if they are unrelated to this change and are recorded before committing.

- [ ] **Step 4: Commit the documentation boundary**

Run:

```bash
cd <repo-root>
git add SKILL.md references/intent-layer-capture.md
git commit -m "Document structural adapter boundaries"
```

Expected: commit succeeds with only documentation changes staged.

## Task 3: Run Final Skill Verification

**Files:**
- Verify: `scripts/check_knowledge_store.py`
- Verify: `tests/test_check_knowledge_store.py`
- Verify: `SKILL.md`
- Verify: `references/intent-layer-capture.md`

- [ ] **Step 1: Run all unit tests**

Run:

```bash
cd <repo-root>
uv run python -m unittest discover -s tests
```

Expected: PASS. Skips for real `sg` integration are acceptable only when the
output says `ast-grep CLI is not installed`.

- [ ] **Step 2: Compile scripts and tests**

Run:

```bash
cd <repo-root>
uv run python -m py_compile scripts/*.py tests/*.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Validate the skill package**

Run:

```bash
cd <repo-root>
uv run --with PyYAML \
  ${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py .
```

Expected: validation succeeds. If `uv` is not available, run the command with
the system Python only if `PyYAML` is installed, then record the exact blocker.

- [ ] **Step 4: Check git state**

Run:

```bash
cd <repo-root>
git status --short
```

Expected: either a clean working tree or only the planning/spec files from this
planning workflow. No generated caches, bytecode, or build output should be
staged.

## Self-Review

- Spec coverage: covered adapter-extra-content detection, valid adapter shapes,
  missing-pointer drift preservation, nested nearest `AGENTS.md`, documentation
  wording, and standard-library-only verification.
- Intentional omissions: no semantic equivalence, no AST expansion, no runtime
  checks, no documentation-generation fixture harness.
- Placeholder scan: no implementation step relies on banned placeholder
  language or undefined helper names.
- Type consistency: tests call `validate(repo)` and inspect existing check
  dictionaries with `id`, `severity`, `path`, and `message`; implementation
  preserves that output structure.
