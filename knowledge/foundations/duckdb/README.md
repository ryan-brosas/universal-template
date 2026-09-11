---
name: duckdb-foundation
description: "Use when porting analytical-database internals — DPhyp join ordering, cardinality estimation, and adaptive-radix-tree index machinery. Source code and direct tests are ground truth."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# duckdb: Join-Order Optimizer + ART Index Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `duckdb`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Join-order planner kernel; Adaptive radix tree index;
  Task scheduler; Buffer pool eviction; Block memory & handles; Buffer
  manager; Data chunks & vectors; Instance lifecycle.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
