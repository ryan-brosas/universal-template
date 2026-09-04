---
name: docmost-foundation
description: 'Use when porting docmost''s realtime collaboration kernel: Redis-synced multi-instance Yjs routing, WS auth ladders, debounced CRDT-to-SQL persistence, and page-tree permissions.'
kind: foundation
invocation: manual
disable-model-invocation: true
---
# docmost: realtime collaboration kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `docmost`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Connection plane; Cluster sync kernel (redis-sync);
  Auth & permission plane; Persistence & history plane; Yjs content surgery.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
