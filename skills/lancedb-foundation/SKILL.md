---
name: lancedb-foundation
description: "Use when porting LanceDB SDK patterns: hybrid search fusion (RRF/rank/normalize), MemWAL LSM read routing + shard-writer writes, IVF/HNSW index build params, compaction/optimize ordering, and query plan/stream wrappers."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# LanceDB: embedded vector database SDK foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `lancedb`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@1b950188c3dc73383707fbab1ce85d4679787e07`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Hybrid sparse+dense fusion; Filter & projection
  planning; MemWAL LSM plane; Index build & maintenance; Plan shape; Execution
  plumbing.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
