# Harness Layout

Use this reference when deciding where repository knowledge belongs.

## Core Rule

`AGENTS.md` is a table of contents. `docs/` is the system of record.

## Preferred Layout

```text
AGENTS.md
ARCHITECTURE.md
docs/
├── design-docs/
│   └── index.md
├── exec-plans/
│   ├── active/
│   └── completed/
├── generated/
├── product-specs/
│   └── index.md
├── references/
├── DESIGN.md
├── FRONTEND.md
├── PLANS.md
├── QUALITY_SCORE.md
├── RELIABILITY.md
└── SECURITY.md
```

Use only the pieces that fit the repository. Do not create phantom docs for
areas that do not exist.

## What Belongs In AGENTS.md

- Repository purpose in one short paragraph.
- Links to architecture, docs indexes, active plans, and test commands.
- Three to five durable invariants agents must not violate.
- Pointers to nested `AGENTS.md` files for major subtrees.

## What Belongs In Docs

- Product behavior, workflows, and user-visible rules.
- Architectural decisions and diagrams.
- Dependency references and `llms.txt`-style vendor summaries.
- Quality scores, reliability notes, and security guidance.
- Execution plans and technical debt trackers.

## Update Order

1. Update leaf docs that describe the changed behavior.
2. Update docs indexes if links or available topics changed.
3. Update nested `AGENTS.md` only when local scope, commands, invariants, or
   routes changed.
4. Update root `AGENTS.md` only when the top-level map or durable invariant
   changed.

## Anti-Patterns From Baseline Testing

| Anti-pattern | Correct action |
| --- | --- |
| Add source-file constants to root `AGENTS.md` | Put behavior facts in docs. |
| Add every touched source file to root `AGENTS.md` | Link only stable docs and maps. |
| Rewrite maps because docs changed nearby | Change maps only when routes changed. |
| Duplicate instructions into `CLAUDE.md` | Use an adapter pointer or flag drift. |
