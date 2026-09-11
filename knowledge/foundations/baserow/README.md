---
name: baserow-foundation
description: "Use when porting Baserow's dynamic-schema kernel: per-user-table Postgres DDL, runtime Django model generation, versioned model caching, link-row twin relations, and MVCC-safe reads beside live ALTERs."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Baserow: dynamic user-table schema kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `baserow`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@d1db1705846ba71ef6054b023d8a1bb81ce59142`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: DDL safety plane; Runtime model plane; Cache
  coherence plane; Relation kernel; Conversion engine.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
