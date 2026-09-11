---
name: teable-foundation
description: "Use when building multi-tenant data platforms on Postgres: computed-field outbox workers, fractional record ordering, DB-trigger undo capture, field dependency graphs, Result-style domain errors, command-replay undo/redo, dual-DB unit of work, fail-open distributed locks, schema-operation ledgers, realtime submit gates, managed full-text/substring search indexes (advisor→executor→reconciler, catalog-derived inventory, HypoPG plan validation, provider capability probing, n-gram semantics comparison), per-cell-type search predicates, computed recompute planning/backfill, enforce-grouped plugin pipelines, transactional computed orchestration with impact-closure fixpoints, and a durable BullMQ outbox trigger bridge with per-base lease admission."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Teable Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `teable`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Background computation; Row ordering; Undo & history;
  Transactions & consistency; Error model; Runtime wiring; Realtime; Search &
  full-text access paths.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
