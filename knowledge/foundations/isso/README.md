---
name: isso-foundation
description: "Use when porting Isso's self-hosted comment-server internals: SQLite comment/thread storage, moderation modes, guard rate limits, signed edit/moderation tokens, notification fanout, sanitizer pipeline, or the multi-mixin WSGI deployment core."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Isso: lightweight comment server — storage, moderation, and embedding kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `isso`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Threaded storage; Schema evolution; Visibility &
  ordering; Moderation & trust; Anti-abuse; Identity & crypto; Embedding
  surface; Boot & serve spine.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
