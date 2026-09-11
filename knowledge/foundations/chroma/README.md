---
name: chroma-foundation
description: 'Use when porting Chroma embedded vector database internals — HNSW segment engine, layered brute-force batches, SQL metadata filter planner, SQLite WAL queue, and the Rust MaxScore/SPANN/HNSW-provider engine.'
license: Apache-2.0
metadata:
  hermes:
    tags: [vector-database, hnsw, metadata-filtering, wal, sparse-retrieval, chroma]
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Chroma: Vector Database Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `chroma`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@93652ec0869489b803fe1682427fc02bd47bec14`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: HNSW label plane; Layered write path; Batch
  accounting; Brute-force twin; Params validation; Filter planner; Metadata
  write path; WAL producer.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
