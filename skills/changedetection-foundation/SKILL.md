---
name: changedetection-foundation
description: "Use when building watch/recheck schedulers, polite pollers, or any multi-worker job fleet — reusable contracts from changedetection.io (Apache-2.0): epoch-priority recheck queue, claim-then-defer UUID mutex, ticker scheduler gate ladder, timezone-pinned schedule windows, per-worker event-loop fleet with health self-repair, quiescence protocol, and memory-hygiene cleanup."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# changedetection.io: Watch-scheduler & worker-fleet Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `changedetection`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@fce24780e74199bf34c62a0d90188cc2fc12f061`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Priority encoding; Queue core; Dedup mutex; Scheduler
  loop; Schedule windows; Worker lifecycle; Watchdog; Failure taxonomy.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
