---
name: turso-foundation
description: "Use when building a SQLite-compatible storage engine: bi-temporal MVCC with Hekaton-style commit dependencies, checksum-chained WAL framing with three-phase commit, b-tree rebalancing, and pin-count durability."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Turso Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `turso`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `1654d1587`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: MVCC core; WAL; B-tree & pager; Logical log;
  Checkpoint & infra; Shared-WAL deep seams (lane B); MVCC deep seams (lane
  B); Logical log & codec deep seams (lane B).
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
