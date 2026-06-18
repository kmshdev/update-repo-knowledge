# AST Change Hints

Use this reference when `knowledge_diff.py` reports `review` or `uncertain`
source changes and structural context would narrow inspection.

## Command

```bash
uv run --script scripts/ast_change_hints.py <repo> \
  --baseline-json baseline.json \
  --knowledge-diff-json diff.json \
  --json
```

## Boundaries

- The helper is optional and advisory.
- AST hints identify changed syntactic structures, not semantic behavior.
- A hint is evidence for where to inspect, not evidence that documentation must
  change.
- Unsupported languages, parser failures, missing files, deleted files, and
  no-hint results fall back to the normal source/docs/test inspection workflow.
- The helper depends on the external `sg` CLI. Python dependencies remain
  standard-library only.

## Output Use

- Treat `ast_status: ok` as a list of structures near changed line ranges.
- Treat `parsed-no-hints` as "ast-grep parsed the file but no configured
  structure overlapped the changed lines."
- Treat `ast-grep-error`, `sg-missing`, and skip statuses as non-blocking.
- Never use this helper to generate docs or decide that docs are stale.
