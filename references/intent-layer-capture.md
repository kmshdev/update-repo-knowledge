# Intent Layer Capture

Use this reference when a repository has nested agent instruction files or
multiple documentation nodes that could own the same fact.

## Placement Rules

- Place facts at semantic boundaries, not every folder.
- Prefer the nearest node that always needs the fact.
- For shared facts, use the least common ancestor.
- Use downlinks for related context outside the ancestor chain.
- Keep nodes small and dense; move detail to docs.

## Leaf-First Update Protocol

1. Identify changed paths from `knowledge_diff.py`.
2. For each changed path, identify the nearest `AGENTS.md` scope.
3. Read the nearest docs node or docs index for that scope.
4. Update leaf docs if behavior, commands, contracts, or invariants changed.
5. Move upward only if the parent map or shared invariant is stale.

## Adapter Policy

Treat non-`AGENTS.md` instruction files as adapters unless the repository says
otherwise.

Valid adapter patterns:

- Symlink to `AGENTS.md`.
- Short file that says canonical instructions live in `AGENTS.md`.
- Generated file with a clear source marker.

Invalid patterns:

- Manual copy of the same instructions.
- Conflicting commands in `AGENTS.md` and `CLAUDE.md`.
- Tool-specific file that silently adds product or architecture facts.

## Uncertainty Handling

If the changed code does not prove intent, write an open question in the
provenance report instead of adding a permanent instruction.

Use this format:

```markdown
## Open Questions

- `path/to/file`: The diff suggests X, but no docs or tests confirm whether Y
  is intended. Leave docs unchanged until confirmed.
```
