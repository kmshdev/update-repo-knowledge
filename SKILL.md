---
name: update-repo-knowledge
description: >-
  Use when repository AGENTS.md, nested agent instructions, docs knowledge
  stores, stale docs, last AGENTS.md commits, provenance, documentation drift,
  CLAUDE.md adapter drift, or post-change agent context refreshes are involved.
---

# Update Repo Knowledge

## Overview

Maintain agent-facing repository knowledge from evidence. Treat `AGENTS.md` as
the route map, `docs/` as the system of record, and source, docs, tests, runtime
checks, and Git history as provenance inputs.

## Required Workflow

1. Read the relevant `AGENTS.md` files and docs indexes.
2. Run `scripts/find_agents_baseline.py <repo> --json` and save the output.
3. Run `scripts/knowledge_diff.py <repo> --baseline-json <baseline.json> --json`.
4. Optionally run `scripts/ast_change_hints.py` for AST-aware inspection hints.
5. Run `scripts/check_knowledge_store.py <repo> --json`.
6. Read only docs and source files needed to resolve `review` or `uncertain`
   findings.
7. For ambiguous diffs, leave durable docs unchanged and write `Open Questions`
   in the provenance report.
8. Update leaf docs first, then docs indexes, then nested `AGENTS.md`, then root
   `AGENTS.md` only if the map, invariant, command, or cross-link changed.
9. Emit a provenance report listing each doc claim changed and the file, diff, or
   validation command that supports it.

For layout details, read `references/harness-layout.md`. For nested intent-node
placement, read `references/intent-layer-capture.md`. For classification and
refusal rules, read `references/update-rubric.md`.

## Script Quick Reference

- Find agent baselines:
  `uv run --script scripts/find_agents_baseline.py <repo> --json`
- Summarize changed files:
  `uv run --script scripts/knowledge_diff.py <repo> --baseline-json baseline.json --json`
- Add optional AST hints:
  `uv run --script scripts/ast_change_hints.py <repo> --baseline-json baseline.json \
  --knowledge-diff-json diff.json --json`
- Check doc store health:
  `uv run --script scripts/check_knowledge_store.py <repo> --json`
- Run repo-level TDD fixture:
  `uv run --script scripts/repo_level_tdd_fixture.py --refresh`

Scripts are evidence gatherers, not doc writers. They classify by path, Git
status, links, and adapter shape; they do not perform AST, semantic, or runtime
analysis. Use their output to decide what to inspect and update.

`ast_change_hints.py` is optional and advisory. It shells out to the external
`sg` ast-grep CLI when available and reports touched syntactic structures for
supported changed files. Read `references/ast-change-hints.md` before relying on
its output.

## Evidence Rules

- Keep root `AGENTS.md` short. Add source-file detail to docs, not root maps.
- Do not write behavior, constants, commands, or architecture claims without a
  supporting source file, diff, test, or runtime check.
- Prefer the nearest nested `AGENTS.md` or docs node that covers the changed
  path. Put shared facts at the least common ancestor, and use downlinks instead
  of copying sibling context.
- In this skill, treat `CLAUDE.md`, Cursor rules, and other tool-specific
  instruction files as adapters unless the repository explicitly says they are
  canonical. Adapters should be symlinks, generated files with a source marker,
  or short pointers to `AGENTS.md`; substantial extra instructions in adapters
  are drift.
- Record uncertainty instead of guessing. An `uncertain` finding with `Open
  Questions` is valid output.

## Refusal Criteria

Do not update repository knowledge when:

- The repo has no `AGENTS.md` and the user did not ask for initial setup.
- The only evidence is a vague diff that does not prove behavior changed.
- A proposed `AGENTS.md` edit would duplicate a fact that belongs in `docs/`.
- The update would manually duplicate canonical instructions into adapters.

Report the blocker with the exact script output or file evidence.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Expanding root `AGENTS.md` with source-file facts | Put facts in leaf docs. |
| Updating nested `AGENTS.md` because nearby docs changed | Change maps only when routes changed. |
| Writing constants into agent instructions | Document behavior in product docs. |
| Treating `CLAUDE.md` as a second source of truth | Convert it to an adapter or flag drift. |
| Skipping provenance | Stop and gather evidence before editing. |

## Forward-Testing Reminder

For skill changes, use RED-GREEN-REFACTOR:

1. Run disposable fixture scenarios without the skill; use target repositories,
   not this skill package, to test repository-knowledge findings.
2. Capture exact failures and rationalizations.
3. Update this skill or references.
4. Forward-test with fixture repos only. `repo_level_tdd_fixture.py` clones the
   official `agentskills/agentskills` repository into `/tmp`.
5. Keep iterating until agents run scripts first, update leaf docs before maps,
   avoid unsupported claims, flag uncertainty, and emit provenance.
