---
name: weaviate-foundation
description: 'Use when porting or operating Weaviate-style vector-engine internals: HNSW filtered search (ACORN/SWEEPING/RRE), tombstone deletion, commit-log WAL rotation, and LSMKV memtable flush/compaction/recovery.'
license: BSD-3-Clause
metadata:
  source: $REFERENCE_ROOT/external/weaviate
  pin: main@adcffc5432aa797c60e3c4e479514054254fae2a
  graph-project: ext-weaviate
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Weaviate Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `weaviate`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `adcffc5432aa797c60e3c4e479514054254fae2a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: ACORN two-hop neighbor expansion; addOne insert path;
  Commit-log rotation; Dead-entrypoint self-repair; ef resolution ladder; HNSW
  filtered-search strategy FSM; Flat-search cutoff; Multivector doc-id mapping.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
