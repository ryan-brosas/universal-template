---
name: qdrant-foundation
description: "Use when porting or re-implementing filtered vector-search machinery: filterable HNSW builds, ACORN/graph dispatch decisions, cardinality-driven prefilter-vs-index planning, WAL durability, hybrid RRF fusion, prefetch-tree query planning, or flush-ordered post-optimize cleanup. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

kind: foundation
invocation: manual
disable-model-invocation: true
---
# Qdrant: vector-engine foundations

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `qdrant`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@74f3e85b9473c62560006c043e13737ce6b48412`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Filtered HNSW build; Payload subgraphs; ACORN
  dispatch; Graph-with-vectors; Quantized search; Estimator; Sparse dispatch;
  WAL format.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
