---
name: milvus-foundation
description: "Use when porting Milvus-style background maintenance into your own system: segment allocation/sealing policies, L0 delete-log compaction eligibility, mix/clustering/sort compaction triggers, a hot-swappable prioritized task queue with per-channel type exclusion, crash-safe persisted task state machines, publish-before-retire meta mutations, target-based reconcilers, storage-format migrations under rate limits, or snapshot-protection gating of destructive rewrites. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

kind: foundation
invocation: manual
disable-model-invocation: true
---
# Milvus: Compaction & Segment Lifecycle Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `milvus`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Scheduling core; Task lifecycle; L0 delete plane;
  Policy family; Meta correctness; Segment plane.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
