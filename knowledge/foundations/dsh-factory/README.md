---
name: dsh-factory-foundation
description: "Use when porting durable dependency-graph task-factory machinery: leader-elected lease-elected schedulers, ready-task claim loops bounded by concurrency, checkout-lane serialization, Agent-session binding with completion channels, orphan-requeue, and mutation-boundary domain logic."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# dsh-factory: durable dependency-graph task factory

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `dsh-factory`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@3405edc7708c83f00ce5a5da881a7fbb260cc019`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Scheduler core; Completion & handoff; Graph kernel;
  Time plane; Durability; Domain services.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
