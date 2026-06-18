# Update Rubric

Use this reference to classify changed files and write the final provenance
report.

## Doc-Impact Classifier

- `review`: Source behavior, public API, command, schema, config, UI, docs, or
  agent instructions changed. Inspect docs and update if stale.
- `uncertain`: A file was deleted, or the diff is ambiguous and no tests/docs
  clarify intent. Verify docs and maps, then record open questions as needed.
- `no-doc-impact`: Binary, lockfile, generated asset, cache, or local metadata
  changed. Usually no docs update is needed.

## Evidence Requirements

Every changed claim needs at least one evidence item:

- Source diff or current source file path.
- Test or build command output.
- Runtime check output.
- Existing doc or architecture decision link.
- User-provided requirement.

Do not cite memory, intuition, or naming alone as evidence.

## Provenance Report Template

```markdown
## Provenance Report

### Changed Claims

| Claim | Updated file | Evidence |
| --- | --- | --- |
| Greeting returns `hello world`. | `docs/api.md` | `src/service.py`, direct runtime check |

### Unchanged Agent Maps

- `AGENTS.md`: unchanged because the top-level route map and durable invariants
  did not change.

### Open Questions

- None.

### Validation

- `uv run --script scripts/find_agents_baseline.py <repo> --json`
- `uv run --script scripts/knowledge_diff.py <repo> --baseline-json baseline.json --json`
- `uv run --script scripts/check_knowledge_store.py <repo> --json`
```

## Refusal Messages

Use direct messages when declining to edit:

- "I found no tracked `AGENTS.md`, so this is initial setup rather than refresh."
- "The diff does not prove a behavior change; I recorded an open question."
- "This fact belongs in leaf docs, not root `AGENTS.md`."
- "The adapter file conflicts with canonical `AGENTS.md`; I flagged drift instead
  of duplicating instructions."
