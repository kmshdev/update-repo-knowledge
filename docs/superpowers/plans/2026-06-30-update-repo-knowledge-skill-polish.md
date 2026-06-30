# Update Repo Knowledge Skill Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the `update-repo-knowledge` skill metadata, static quality, benchmark scenarios, and evaluation coverage while preserving strict repository-knowledge checker semantics.

**Architecture:** Make changes from the repository root, validate there, then copy the validated files into the installed skill at `$HOME/.agents/skills/update-repo-knowledge`. Keep `SKILL.md` concise and put evaluation detail in docs so the skill keeps using progressive disclosure. Use disposable target repositories for behavior validation instead of weakening checker behavior for this skill package.

**Tech Stack:** Codex skills, `agents/openai.yaml`, Python 3.12 stdlib scripts, `unittest`, `uv run --script`, `ast-grep` CLI via `sg`, Plugin Eval bundled CLI script.

---

## Source References

Use these references while implementing and evaluating:

- OpenAI Codex skills optional metadata: `https://developers.openai.com/codex/skills#optional-metadata`
- OpenAI harness engineering article: `https://openai.com/index/harness-engineering/`
- Matklad architecture note: `https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html`
- Intent Layer article: `https://intent-systems.com/blog/intent-layer`
- AGENTS.md guide: `https://www.morphllm.com/agents-md-guide`
- Local guide: `$HOME/.codex/.agent/agents-md-skills-md.md`
- Installed skill target: `$HOME/.agents/skills/update-repo-knowledge`
- Source skill repo: repository root

## File Structure

- Modify `agents/openai.yaml`: Codex app metadata, default prompt, implicit invocation policy, tool dependencies.
- Modify `scripts/ast_change_hints.py`: split summary accounting out of `summarize()` to reduce static complexity.
- Modify `tests/test_ast_change_hints.py`: unit coverage for the new summary accounting helper and `summarize()` integration.
- Create `.plugin-eval/benchmark.json`: realistic Plugin Eval scenarios for the three required skill outcomes.
- Create `docs/evaluations/2026-06-30-agents-guidance-alignment.md`: evaluation plan for AGENTS.md guidance, update workflow, and alignment with source links.
- Modify `$HOME/.agents/skills/update-repo-knowledge/agents/openai.yaml`: sync after source validation.
- Modify `$HOME/.agents/skills/update-repo-knowledge/scripts/ast_change_hints.py`: sync after source validation.
- Modify `$HOME/.agents/skills/update-repo-knowledge/tests/test_ast_change_hints.py`: sync after source validation.
- Modify `$HOME/.agents/skills/update-repo-knowledge/.plugin-eval/benchmark.json`: sync or replace after source validation.

## Strict Semantics To Preserve

- `check_knowledge_store.py` must keep reporting `missing-root-agents` as an error in target repos.
- `docs/` without `index.md` must stay a warning in target repos.
- Adapter files such as `CLAUDE.md`, `GEMINI.md`, and `.cursorrules` remain adapters unless the repo explicitly declares them canonical.
- Pointer-shaped adapters with extra instruction content remain drift.
- `knowledge_diff.py` remains path/status based; semantic and runtime analysis stay out of scope.
- Repo-level behavior must be validated with disposable target repos under `/tmp`, not by relaxing checks for this skill repo.

### Task 1: Improve Codex App Skill Metadata

**Files:**
- Modify: `agents/openai.yaml`
- Later sync: `$HOME/.agents/skills/update-repo-knowledge/agents/openai.yaml`

- [ ] **Step 1: Replace source metadata with explicit optional metadata**

Replace the entire file `agents/openai.yaml` with:

```yaml
interface:
  display_name: "Update Repo Knowledge"
  short_description: "Refresh AGENTS.md maps, docs knowledge stores, adapter drift checks, and provenance after repository changes."
  default_prompt: "Update repository knowledge from current git evidence. Keep AGENTS.md concise, update leaf docs first, preserve adapter boundaries, and emit a provenance report."

policy:
  allow_implicit_invocation: true

dependencies:
  tools:
    - type: "cli"
      value: "git"
      description: "Reads repository status, tracked AGENTS.md baselines, and changed files."
    - type: "cli"
      value: "uv"
      description: "Runs the skill's Python evidence-gathering scripts."
    - type: "cli"
      value: "sg"
      description: "Optional ast-grep structural hints for changed source files."
```

- [ ] **Step 2: Validate YAML parses and key fields exist**

Run:

```bash
cd <repo-root>
uv run --with pyyaml python - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("agents/openai.yaml").read_text())
assert data["interface"]["display_name"] == "Update Repo Knowledge"
assert data["policy"]["allow_implicit_invocation"] is True
tools = {item["value"] for item in data["dependencies"]["tools"]}
assert tools == {"git", "uv", "sg"}
print("openai.yaml metadata ok")
PY
```

Expected:

```text
openai.yaml metadata ok
```

- [ ] **Step 3: Commit metadata change**

Run:

```bash
cd <repo-root>
git add agents/openai.yaml
git commit -m "docs(skill): clarify update repo knowledge metadata"
```

Expected: commit succeeds without hook bypass flags.

### Task 2: Split Summary Accounting Out Of `ast_change_hints.py`

**Files:**
- Modify: `scripts/ast_change_hints.py`
- Modify: `tests/test_ast_change_hints.py`
- Later sync: `$HOME/.agents/skills/update-repo-knowledge/scripts/ast_change_hints.py`
- Later sync: `$HOME/.agents/skills/update-repo-knowledge/tests/test_ast_change_hints.py`

- [ ] **Step 1: Add failing tests for summary accounting**

Append this test class to `tests/test_ast_change_hints.py` after `DiffParsingTests`:

```python
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
            path = str(change["path"])
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
                        {"path": "one.py", "status": "M", "agent_file": "AGENTS.md", "doc_impact": "review"},
                        {"path": "two.py", "status": "M", "agent_file": "AGENTS.md", "doc_impact": "review"},
                        {"path": "three.txt", "status": "M", "agent_file": "AGENTS.md", "doc_impact": "review"},
                        {"path": "four.lock", "status": "M", "agent_file": "AGENTS.md", "doc_impact": "no-doc-impact"},
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
        self.assertEqual([change["path"] for change in result["changes"]], ["one.py", "two.py", "three.txt", "four.lock"])
```

- [ ] **Step 2: Run the targeted tests and verify failure**

Run:

```bash
cd <repo-root>
python -m unittest tests.test_ast_change_hints.SummaryAccountingTests -v
```

Expected: fail with an error like:

```text
AttributeError: module 'ast_change_hints' has no attribute 'empty_summary'
```

- [ ] **Step 3: Add helper functions and simplify `summarize()`**

In `scripts/ast_change_hints.py`, add these functions after `analyze_change()` and replace the existing `summarize()` with the version below:

```python
def empty_summary() -> dict[str, int]:
    return {
        "eligible_files": 0,
        "analyzed_files": 0,
        "unsupported_files": 0,
        "skipped_files": 0,
    }


def record_analysis_state(summary: dict[str, int], state: str) -> None:
    if state == "eligible":
        summary["eligible_files"] += 1
        return
    if state == "analyzed":
        summary["eligible_files"] += 1
        summary["analyzed_files"] += 1
        return
    if state == "unsupported":
        summary["unsupported_files"] += 1
        return
    summary["skipped_files"] += 1


def baseline_agents(baseline_data: dict[str, object]) -> list[dict[str, object]]:
    return [
        entry
        for entry in baseline_data.get("agent_files", [])
        if isinstance(entry, dict) and entry.get("last_commit")
    ]


def iter_change_objects(diff_data: dict[str, object]) -> list[dict[str, object]]:
    return [
        change
        for change in diff_data.get("changes", [])
        if isinstance(change, dict)
    ]


def summarize(
    repo: Path,
    baseline_data: dict[str, object],
    diff_data: dict[str, object],
    sg_path: Optional[str] = None,
) -> dict[str, object]:
    agents = baseline_agents(baseline_data)
    sg_info = find_sg(sg_path)
    changes = []
    summary = empty_summary()

    for change in iter_change_objects(diff_data):
        entry, state = analyze_change(repo, change, agents, sg_info)
        changes.append(entry)
        record_analysis_state(summary, state)

    return {"repo": str(repo), "sg": sg_info, "summary": summary, "changes": changes}
```

- [ ] **Step 4: Run targeted tests and verify pass**

Run:

```bash
cd <repo-root>
python -m unittest tests.test_ast_change_hints.SummaryAccountingTests -v
```

Expected:

```text
Ran 2 tests

OK
```

- [ ] **Step 5: Run full Python unit tests**

Run:

```bash
cd <repo-root>
python -m unittest discover -s tests -v
```

Expected: all tests pass. Tests that depend on missing local `sg` may be skipped.

- [ ] **Step 6: Run Plugin Eval static analysis and verify complexity warning is gone or lower**

Run:

```bash
cd <repo-root>
node $HOME/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js analyze . --format markdown
```

Expected: score remains grade `A`; the `py-complexity-high` warning is absent. If the warning remains but reports a lower max complexity, inspect the reported function and repeat the same helper-extraction pattern before continuing.

- [ ] **Step 7: Commit complexity refactor**

Run:

```bash
cd <repo-root>
git add scripts/ast_change_hints.py tests/test_ast_change_hints.py
git commit -m "refactor(skill): split ast hint summary accounting"
```

Expected: commit succeeds without hook bypass flags.

### Task 3: Add Realistic Plugin Eval Benchmark Scenarios

**Files:**
- Create: `.plugin-eval/benchmark.json`
- Later sync: `$HOME/.agents/skills/update-repo-knowledge/.plugin-eval/benchmark.json`

- [ ] **Step 1: Create benchmark directory and benchmark config**

Run:

```bash
cd <repo-root>
mkdir -p .plugin-eval
```

Create `.plugin-eval/benchmark.json` with:

```json
{
  "kind": "plugin-eval-benchmark",
  "schemaVersion": 2,
  "version": 2,
  "targetKind": "skill",
  "targetName": "update-repo-knowledge",
  "runner": {
    "type": "codex-cli",
    "model": "gpt-5.5",
    "sandbox": "workspace-write",
    "approvalPolicy": "never",
    "extraArgs": []
  },
  "workspace": {
    "sourcePath": "/tmp/update-repo-knowledge-benchmark-workspace",
    "setupMode": "copy",
    "preserve": "on-failure"
  },
  "targetProvisioning": {
    "mode": "isolated-skill-home"
  },
  "verifiers": {
    "commands": [
      "test -f Provenance.md",
      "grep -q \"Changed Claims\" Provenance.md",
      "grep -q \"Validation\" Provenance.md"
    ]
  },
  "notes": [
    "Use disposable fixture repositories only. Do not benchmark against a real project checkout.",
    "Each scenario must prove the skill runs evidence scripts before changing durable docs.",
    "Strict checker semantics are expected: missing AGENTS.md remains an initial-setup blocker unless the prompt asks for setup."
  ],
  "setupQuestions": [
    "Does the run invoke find_agents_baseline.py, knowledge_diff.py, and check_knowledge_store.py before editing docs?",
    "Does the run keep AGENTS.md concise and update leaf docs first?",
    "Does the run flag adapter drift instead of duplicating instructions into CLAUDE.md?",
    "Does the run leave durable docs unchanged when evidence does not prove behavior changed?",
    "Does the final answer include provenance and validation evidence?"
  ],
  "scenarios": [
    {
      "id": "polyglot-post-change-doc-refresh",
      "title": "Post-change docs refresh in a polyglot repo",
      "purpose": "Verify that the skill handles a repo with Python, TypeScript, and Rust source changes without assuming one project language.",
      "userInput": "Use the local Codex skill \"update-repo-knowledge\". In this disposable repo, refresh repository knowledge after the staged Python, TypeScript, and Rust source changes. Keep AGENTS.md short, update leaf docs before maps, and write a provenance report to Provenance.md.",
      "successChecklist": [
        "The run invokes the baseline, diff, and knowledge-store checker scripts before editing docs.",
        "The run inspects only source and docs needed for review or uncertain findings.",
        "The run updates docs for proven behavior changes and avoids language-specific assumptions.",
        "The run leaves AGENTS.md unchanged unless a map, invariant, command, or cross-link changed.",
        "Provenance.md lists changed claims and cites source files, diffs, tests, or validation commands."
      ]
    },
    {
      "id": "adapter-drift-between-agents-and-claude",
      "title": "Adapter drift between AGENTS.md and CLAUDE.md",
      "purpose": "Verify that tool-specific instruction files are treated as adapters unless declared canonical.",
      "userInput": "Use the local Codex skill \"update-repo-knowledge\". This disposable repo has AGENTS.md and a CLAUDE.md file with extra manual instructions. Detect and report adapter drift without copying canonical instructions into CLAUDE.md. Write findings and validation to Provenance.md.",
      "successChecklist": [
        "The run identifies CLAUDE.md as an adapter under the nearest AGENTS.md scope.",
        "The run reports adapter drift or adapter extra content with exact file evidence.",
        "The run does not manually duplicate AGENTS.md content into CLAUDE.md.",
        "The run preserves strict checker output instead of weakening validation semantics.",
        "Provenance.md records unchanged maps and open questions when intent is not proven."
      ]
    },
    {
      "id": "no-op-when-diff-does-not-prove-doc-change",
      "title": "No-op or refusal when evidence is insufficient",
      "purpose": "Verify that the skill narrows or refuses durable docs edits when a diff is vague.",
      "userInput": "Use the local Codex skill \"update-repo-knowledge\". The disposable repo has a vague source diff that does not prove user-visible behavior, architecture, commands, or agent routes changed. Do not update durable docs unless evidence supports it. Write Provenance.md with open questions and validation.",
      "successChecklist": [
        "The run gathers baseline, diff, and checker evidence before deciding.",
        "The run leaves durable docs unchanged when the diff does not prove a changed claim.",
        "The run records an Open Questions section instead of guessing intent.",
        "The run reports the exact script output or file evidence behind the no-op decision.",
        "The final answer states that no durable docs were changed."
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate benchmark JSON**

Run:

```bash
cd <repo-root>
python -m json.tool .plugin-eval/benchmark.json >/tmp/update-repo-knowledge-benchmark.json
```

Expected: command exits `0` and writes formatted JSON to `/tmp/update-repo-knowledge-benchmark.json`.

- [ ] **Step 3: Ask Plugin Eval for the next benchmark command**

Run:

```bash
cd <repo-root>
node $HOME/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js start . --request "Help me benchmark this skill." --format markdown
```

Expected: output routes to the benchmark workflow and references `.plugin-eval/benchmark.json`.

- [ ] **Step 4: Commit benchmark config**

Run:

```bash
cd <repo-root>
git add .plugin-eval/benchmark.json
git commit -m "test(skill): add repo knowledge benchmark scenarios"
```

Expected: commit succeeds without hook bypass flags.

### Task 4: Add AGENTS.md Guidance Alignment Evaluation Plan

**Files:**
- Create: `docs/evaluations/2026-06-30-agents-guidance-alignment.md`

- [ ] **Step 1: Create evaluation docs directory**

Run:

```bash
cd <repo-root>
mkdir -p docs/evaluations
```

- [ ] **Step 2: Write alignment evaluation plan**

Create `docs/evaluations/2026-06-30-agents-guidance-alignment.md` with:

```markdown
# AGENTS.md Guidance Alignment Evaluation

## Purpose

Evaluate whether `update-repo-knowledge` maintains repository guidance in the style required by harness engineering, architecture codemaps, the Intent Layer, AGENTS.md guidance, and Codex skill metadata.

## Scope

This evaluation covers:

- Whether `AGENTS.md` remains a concise route map.
- Whether deeper behavior and architecture claims live in docs.
- Whether nested instruction files are placed at semantic boundaries.
- Whether adapter files avoid becoming second sources of truth.
- Whether docs updates are backed by current source, diffs, tests, runtime checks, or user requirements.
- Whether the skill triggers implicitly for repository-knowledge work without triggering for unrelated refactors.

## Source Alignment Matrix

| Source | Principle | Evidence To Check | Pass Condition |
| --- | --- | --- | --- |
| OpenAI harness engineering | `AGENTS.md` routes to durable docs and executable checks. | `SKILL.md`, `references/harness-layout.md`, benchmark outputs. | Root maps stay short; changed claims cite source, diff, test, runtime, or user evidence. |
| Matklad `ARCHITECTURE.md` | Architecture docs provide a durable codemap and invariants, not volatile implementation detail. | Updated docs and unchanged maps in `Provenance.md`. | Durable architecture facts are documented in docs; volatile source constants are not copied into `AGENTS.md`. |
| Intent Layer | Context nodes sit at semantic boundaries and use progressive disclosure. | Nested `AGENTS.md` ownership in `knowledge_diff.py` output and `intent-layer-capture.md`. | Facts are placed at the nearest owning node or least common ancestor; sibling context uses links instead of duplicated content. |
| Morph AGENTS.md guide | AGENTS content is exact, concise, command-oriented, and non-redundant. | Final `AGENTS.md` diff and provenance report. | `AGENTS.md` names commands, boundaries, and routes; it does not repeat README or docs detail. |
| Local `agents-md-skills-md.md` guide | AGENTS and skills remain distinct surfaces. | Skill docs and adapter checks. | Project conventions stay in AGENTS/docs; reusable workflow stays in the skill; adapters point to canonical instructions. |
| OpenAI Codex optional metadata | Skill description and metadata support correct implicit invocation. | `SKILL.md` frontmatter and `agents/openai.yaml`. | Description front-loads trigger terms; `allow_implicit_invocation` remains true; dependencies are declared. |

## Evaluation Scenarios

### Scenario 1: Polyglot Post-Change Refresh

Fixture shape:

```text
AGENTS.md
docs/index.md
docs/services/index.md
src/service.py
web/client.ts
crates/core/src/lib.rs
```

Required behavior:

- Run `find_agents_baseline.py`, `knowledge_diff.py`, and `check_knowledge_store.py`.
- Inspect only files classified as `review` or `uncertain`.
- Update leaf docs for proven behavior changes.
- Leave root `AGENTS.md` unchanged unless its route map changed.
- Emit `Provenance.md` with changed claims, unchanged maps, open questions, and validation.

### Scenario 2: Adapter Drift

Fixture shape:

```text
AGENTS.md
CLAUDE.md
docs/index.md
```

Required behavior:

- Treat `CLAUDE.md` as an adapter unless the repo declares it canonical.
- Warn on extra instruction content in pointer-shaped adapters.
- Do not duplicate canonical instructions into `CLAUDE.md`.
- Preserve `adapter-extra-content` or `adapter-drift` checker output.

### Scenario 3: Insufficient Evidence No-Op

Fixture shape:

```text
AGENTS.md
docs/index.md
src/internal_name_change.py
```

Required behavior:

- Gather evidence first.
- Leave durable docs unchanged when a diff does not prove a behavior, command, architecture, or route change.
- Record an `Open Questions` entry in `Provenance.md`.
- Final answer states no durable docs changed.

## Metrics

| Metric | Target |
| --- | --- |
| Evidence-first rate | 100 percent of benchmark runs invoke baseline, diff, and checker before docs edits. |
| Root map restraint | 0 root `AGENTS.md` edits when only leaf behavior changed. |
| Unsupported claim count | 0 changed claims without source, diff, test, runtime, or user evidence. |
| Adapter duplication count | 0 manual copies of canonical instructions into adapters. |
| No-op correctness | 100 percent of insufficient-evidence scenarios leave durable docs unchanged. |
| Implicit invocation precision | Skill activates for AGENTS/docs/provenance/drift prompts and does not activate for ordinary implementation-only prompts. |

## Verification Commands

```bash
python -m unittest discover -s tests -v
uv run --script scripts/repo_level_tdd_fixture.py --refresh
node $HOME/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js analyze . --format markdown
python -m json.tool .plugin-eval/benchmark.json >/tmp/update-repo-knowledge-benchmark.json
```

## Decision Rule

The skill is aligned when all unit tests pass, the repo-level disposable fixture keeps strict checker semantics, Plugin Eval remains grade `A`, and benchmark scenario review shows evidence-first updates with concise AGENTS maps and no adapter duplication.
```

- [ ] **Step 3: Review for banned placeholders and exact source names**

Run:

```bash
cd <repo-root>
python - <<'PY'
from pathlib import Path

text = Path("docs/evaluations/2026-06-30-agents-guidance-alignment.md").read_text()
patterns = [
    "T" + "BD",
    "TO" + "DO",
    "implement " + "later",
    "fill in " + "details",
    "appropriate error " + "handling",
    "Write tests for " + "the above",
    "Similar to " + "Task",
]
matches = [pattern for pattern in patterns if pattern in text]
if matches:
    raise SystemExit(f"placeholder patterns found: {matches}")
print("placeholder scan passed")
PY
```

Expected:

```text
placeholder scan passed
```

- [ ] **Step 4: Commit evaluation plan**

Run:

```bash
cd <repo-root>
git add docs/evaluations/2026-06-30-agents-guidance-alignment.md
git commit -m "docs(skill): add agents guidance alignment evaluation"
```

Expected: commit succeeds without hook bypass flags.

### Task 5: Run Final Validation And Sync Installed Skill

**Files:**
- Source files from Tasks 1-4
- Sync target: `$HOME/.agents/skills/update-repo-knowledge`

- [ ] **Step 1: Run full source validation**

Run:

```bash
cd <repo-root>
python -m unittest discover -s tests -v
python -m py_compile scripts/*.py
uv run --with pyyaml python - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("agents/openai.yaml").read_text())
assert data["policy"]["allow_implicit_invocation"] is True
assert "AGENTS.md maps" in data["interface"]["short_description"]
print("metadata validation passed")
PY
python -m json.tool .plugin-eval/benchmark.json >/tmp/update-repo-knowledge-benchmark.json
```

Expected:

```text
metadata validation passed
```

and all unit tests and compile checks pass.

- [ ] **Step 2: Run repo-level disposable fixture**

Run:

```bash
cd <repo-root>
uv run --script scripts/repo_level_tdd_fixture.py --refresh
```

Expected: the fixture runs against `/tmp/update-repo-knowledge-tdd/agentskills`. Strict checker findings such as `missing-root-agents`, `adapter-drift`, or `missing-docs-index` are acceptable when they are the expected target-repo behavior.

- [ ] **Step 3: Run Plugin Eval analysis**

Run:

```bash
cd <repo-root>
node $HOME/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js analyze . --format markdown
```

Expected: grade `A`; no new frontmatter, link, metadata, or budget failures.

- [ ] **Step 4: Sync validated files into installed skill**

Run:

```bash
cd <repo-root>
mkdir -p $HOME/.agents/skills/update-repo-knowledge/.plugin-eval
cp agents/openai.yaml $HOME/.agents/skills/update-repo-knowledge/agents/openai.yaml
cp scripts/ast_change_hints.py $HOME/.agents/skills/update-repo-knowledge/scripts/ast_change_hints.py
cp tests/test_ast_change_hints.py $HOME/.agents/skills/update-repo-knowledge/tests/test_ast_change_hints.py
cp .plugin-eval/benchmark.json $HOME/.agents/skills/update-repo-knowledge/.plugin-eval/benchmark.json
```

Expected: commands exit `0`.

- [ ] **Step 5: Validate installed skill**

Run:

```bash
cd $HOME/.agents/skills/update-repo-knowledge
python -m unittest tests.test_ast_change_hints.SummaryAccountingTests -v
python -m json.tool .plugin-eval/benchmark.json >/tmp/installed-update-repo-knowledge-benchmark.json
uv run --with pyyaml python - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("agents/openai.yaml").read_text())
assert data["policy"]["allow_implicit_invocation"] is True
assert {item["value"] for item in data["dependencies"]["tools"]} == {"git", "uv", "sg"}
print("installed skill validation passed")
PY
```

Expected:

```text
installed skill validation passed
```

- [ ] **Step 6: Commit final source repo state**

Run:

```bash
cd <repo-root>
git status --short
git add .
git commit -m "chore(skill): validate repo knowledge skill polish"
```

Expected: commit succeeds if there are remaining source repo changes. If `git status --short` is empty, skip this commit and record that all prior tasks were already committed.

## Self-Review

- Spec coverage: Tasks 1, 3, and 4 cover metadata, implicit invocation, benchmark scenarios, and alignment evaluation. Task 2 covers Plugin Eval complexity. Task 5 preserves strict checker semantics through source and installed-skill validation.
- Placeholder scan: The plan avoids deferred implementation markers and gives exact file paths, code blocks, commands, and expected outputs.
- Type consistency: New helper names are `empty_summary`, `record_analysis_state`, `baseline_agents`, and `iter_change_objects`; tests and implementation use the same names.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-30-update-repo-knowledge-skill-polish.md`. Two execution options:

1. Subagent-Driven (recommended) - Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints.
