---
name: analytics-foundation
description: Use when porting or debugging privacy-analytics engine internals — ClickHouse query planning with table partitioning and subquery joins, session metric sign arithmetic, timeSlots smearing, goal array-index joins, filter-to-SQL compilation, batched RowBinary ingestion, per-user serialization, comparison-period arithmetic, or tracker engagement protocol.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Plausible Analytics: ClickHouse web-analytics foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `analytics`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@9cc669b97ece3ecd37fcb3950791cb3873d7944d`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Query execution; Query planning; Metrics math;
  Dimension compilation; Session state; Ingestion; Caching substrate; Time
  semantics.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
