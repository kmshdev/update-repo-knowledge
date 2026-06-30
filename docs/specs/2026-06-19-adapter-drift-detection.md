# Adapter Drift Detection Skill Update Spec

## Objective

Tighten `update-repo-knowledge` adapter checks so pointer-shaped adapter files
cannot silently carry extra repository instructions. Keep the skill boundary
structural and deterministic: this update must not compare semantic equivalence,
generate documentation, or change `knowledge_diff.py` classifications.

## Background

The skill treats `AGENTS.md` as the route map and `docs/` as the system of
record. Tool-specific instruction files such as `CLAUDE.md`, `GEMINI.md`, and
`.cursorrules` are adapters unless a repository explicitly declares one of them
canonical.

Current `check_knowledge_store.py` behavior accepts any adapter text containing
`AGENTS.md` or `canonical`. That catches manual adapter files without pointers,
but it also lets this drift pattern pass:

```markdown
See AGENTS.md for canonical instructions.

Also use this extra command, architecture fact, or product policy.
```

That is still a structural issue, not a semantic one. The fix should warn on
adapter shape that is too large or instruction-like after it points at the
canonical file.

## Non-Goals

- Avoid semantic adapter equivalence checking.
- Skip LLM review, embeddings, AST analysis, or runtime behavior checks.
- Keep `knowledge_diff.py` JSON schema and path/status routing unchanged.
- Keep tests out of a documentation-generation fixture harness.
- Avoid new Python package dependencies.

## Proposed Change

Update `scripts/check_knowledge_store.py` with a narrow adapter-shape classifier:

1. Symlink adapters remain valid.
2. Short pointer adapters remain valid when they mention `AGENTS.md` or
   `canonical`.
3. Generated adapters remain valid when they have an explicit generated marker
   and point back to `AGENTS.md` or canonical instructions.
4. Adapters with no accepted pointer continue to warn as `adapter-drift`.
5. Adapters that contain an accepted pointer plus substantial extra content warn
   as `adapter-extra-content`.

Use deterministic thresholds, for example:

- `short pointer`: at most 5 nonblank lines and at most 500 characters.
- `generated adapter`: first 10 lines contain a generated marker and an
  accepted pointer.
- `extra content`: accepted pointer present, but the file exceeds the short
  pointer thresholds and is not recognized as generated.

The warning message should tell agents what to do:

```text
CLAUDE.md points to AGENTS.md but contains additional instruction content; keep
adapters as short canonical pointers or declare this adapter canonical in
AGENTS.md.
```

## Skill Documentation Updates

Keep `SKILL.md` concise. Add at most one sentence if needed:

```markdown
Adapter files should be symlinks, generated files with a generated provenance
marker, or short pointers to `AGENTS.md`; substantial extra instructions in
adapters are treated as drift.
```

Update `references/intent-layer-capture.md` with the concrete adapter boundary:

```markdown
Adapter checks are structural. A valid adapter is a symlink, a short canonical
pointer to `AGENTS.md`, or a generated file with an explicit generated
provenance marker.
Pointer files that also contain product facts, architecture facts, commands, or
policy instructions should be treated as adapter drift unless the repository
declares that adapter canonical.
```

Do not document any semantic-equivalence guarantee. Use this wording:

```markdown
Passing adapter checks means the adapter has an accepted structural shape; it
does not prove two instruction files are semantically equivalent.
```

## Test Plan

Use standard-library `unittest` and temporary repositories. Add
`tests/test_check_knowledge_store.py`.

Write the tests before changing behavior:

1. `test_short_pointer_adapter_passes`
   - Create `AGENTS.md` and `CLAUDE.md` with only a short pointer.
   - Assert no `adapter-*` warning.
2. `test_symlink_adapter_passes`
   - Symlink `CLAUDE.md` to `AGENTS.md`.
   - Assert no adapter warning.
3. `test_generated_adapter_with_source_marker_passes`
   - Create a generated adapter that points to `AGENTS.md`.
   - Assert no adapter warning.
4. `test_manual_adapter_without_pointer_warns`
   - Create `CLAUDE.md` with standalone instructions and no pointer.
   - Assert `adapter-drift`.
5. `test_pointer_with_extra_instruction_content_warns`
   - Create `CLAUDE.md` that points to `AGENTS.md` and adds commands or policy.
   - Assert `adapter-extra-content`.
6. `test_nested_agent_scope_uses_nearest_agents_file`
   - Create root and nested `AGENTS.md` files with an adapter under the nested
     tree.
   - Assert the warning message names the nearest `AGENTS.md`.

Existing AST tests should remain unchanged.

## Verification Commands

Run these from the repository root:

```bash
uv run python -m unittest discover -s tests
uv run python -m py_compile scripts/*.py tests/*.py
uv run --with PyYAML ${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py .
```

If `uv` is unavailable in the execution environment, use the system Python for
the first two commands and record that skill validation was not run.

## Acceptance Criteria

- A pointer-only adapter still passes.
- A symlink adapter still passes.
- A generated adapter with a generated provenance marker still passes.
- A manual adapter with no pointer still emits `adapter-drift`.
- A pointer adapter with substantial extra instruction content emits
  `adapter-extra-content`.
- `check_knowledge_store.py` remains standard-library only.
- `knowledge_diff.py` and `ast_change_hints.py` behavior is unchanged.
- `SKILL.md` remains a concise routing file; detailed policy lives in
  references.

## Implementation Sequence

1. Add failing tests for the adapter-extra-content case and existing valid
   adapter shapes.
2. Add a small adapter-shape helper inside `check_knowledge_store.py`.
3. Update warning emission while preserving existing JSON output structure.
4. Update `references/intent-layer-capture.md` and optionally `SKILL.md`.
5. Run the verification commands and inspect warnings, not just exit codes.

## Decision

Patch narrowly. This is the only remaining post-AST limitation that is both
valid and immediately actionable without changing the skill into a semantic
analyzer or documentation writer.
