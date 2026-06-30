# AGENTS.md Guidance Alignment Evaluation

## Purpose

Evaluate whether `update-repo-knowledge` maintains repository guidance in the
style required by harness engineering, architecture codemaps, the Intent Layer,
AGENTS.md guidance, and Codex skill metadata.

## Scope

This evaluation covers:

- Whether `AGENTS.md` remains a concise route map.
- Whether deeper behavior and architecture claims live in docs.
- Whether nested instruction files are placed at semantic boundaries.
- Whether adapter files avoid becoming second sources of truth.
- Whether docs updates are backed by current source, diffs, tests, runtime
  checks, or user requirements.
- Whether the skill triggers implicitly for repository-knowledge work without
  triggering for unrelated refactors.

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

- Run `find_agents_baseline.py`, `knowledge_diff.py`, and
  `check_knowledge_store.py`.
- Inspect only files classified as `review` or `uncertain`.
- Update leaf docs for proven behavior changes.
- Leave root `AGENTS.md` unchanged unless its route map changed.
- Emit `Provenance.md` with changed claims, unchanged maps, open questions, and
  validation.

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
- Leave durable docs unchanged when a diff does not prove a behavior, command,
  architecture, or route change.
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
python3 -m unittest discover -s tests -v
uv run --script scripts/repo_level_tdd_fixture.py --refresh
node /Users/kmsh/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js analyze /Users/kmsh/Researcher/update-repo-knowledge --format markdown
python3 -m json.tool .plugin-eval/benchmark.json >/tmp/update-repo-knowledge-benchmark.json
```

## Decision Rule

The skill is aligned when all unit tests pass, the repo-level disposable fixture
keeps strict checker semantics, Plugin Eval remains grade `A` on the installed
skill bundle, and benchmark scenario review shows evidence-first updates with
concise AGENTS maps and no adapter duplication.
