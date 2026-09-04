---
name: grist-core-foundation
description: "Use when building document-database or collaboration-server infrastructure: crash-safe webhook delivery queues, versioned SQLite migrations with nested transactions, per-key work scheduling and mutexes, snapshot retention ladders, redis worker assignment with elections, TTL system permits, composable change summaries, pub-sub cache invalidation, userspace CPU throttling, affinity-safe embedded value storage, online schema evolution, OT action commit pipelines with rejected-action salvage, idempotent document shutdown ladders, election-gated multi-replica housekeeping, Doom-style cascading deletion, multi-source read ladders with cache invalidation, counter-gated keep-open inactivity timers, plan-driven delete-only freezes, checksum-verified hosted storage claim/push, eventually-consistent object-store decorators, parentRef-linked action history with branch tips and hash-checked sharing, period-gated history pruning, compensating undo-block transactions over live-applied actions, five-layer confinement for…"
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Grist Core Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `grist-core`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@b83224bbe9c88910dfeb28922df254a26f702f68`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Outbound event delivery; Embedded database lifecycle;
  Document storage engine (DocStorage); Collaboration & lifecycle governance;
  Durability & attachment GC; Hosted multi-worker storage; Per-resource
  background work; Versioned storage.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
