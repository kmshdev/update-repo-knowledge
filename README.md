# update-repo-knowledge

Codex skill for maintaining agent-facing repository knowledge from evidence.

The skill treats `AGENTS.md` as a route map, `docs/` as the system of record,
and source files, docs, tests, runtime checks, and Git history as provenance
inputs. Its scripts gather evidence; they do not write documentation or infer
semantic behavior automatically.

## Install

Copy or clone this repository into a Codex skills directory:

```bash
git clone git@github.com:kmshdev/update-repo-knowledge.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/update-repo-knowledge"
```

## Use

Invoke the skill when repository instructions, docs knowledge stores, adapter
drift, or post-change context refreshes are involved.

```bash
uv run --script scripts/find_agents_baseline.py <repo> --json > baseline.json
uv run --script scripts/knowledge_diff.py <repo> \
  --baseline-json baseline.json \
  --json > diff.json
uv run --script scripts/check_knowledge_store.py <repo> --json
```

Optional AST-aware hints require the external `sg`/ast-grep CLI:

```bash
uv run --script scripts/ast_change_hints.py <repo> \
  --baseline-json baseline.json \
  --knowledge-diff-json diff.json \
  --json
```

## Validate

```bash
uv run python -m unittest discover -s tests
uv run python -m py_compile scripts/*.py tests/*.py
```

## License

MIT
