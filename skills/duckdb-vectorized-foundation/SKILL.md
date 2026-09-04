---
name: duckdb-vectorized-foundation
description: "Use when porting DuckDB's vectorized execution core — vector formats, expression executor, adaptive filters — or building a tuple-filter pipeline that must handle flat, constant, dictionary, sequence, and shredded encodings without materialization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# DuckDB: vectorized execution core (vector formats, expression executor, adaptive filters)

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `duckdb-vectorized`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Unified read format (Orrify); Tuple indirection;
  Zero-copy algebra; Format matrix; Constant folding; CASE funnel; Conjunction
  funnel; Adaptive filter order.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
