---
name: postal-foundation
description: "Use when building SMTP mail-server delivery engines: DB-backed message queues with atomic claim locks, worker processes with role election, guard-chain message processing ladders, SMTP session reuse across batches, SSRF-guarded webhook delivery, per-server sharded message databases."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Postal Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `postal`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Queue claim plane; Worker runtime; Role election;
  Processing spine; Outgoing gates; Incoming gates; SMTP transport; Outcome
  contract.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
