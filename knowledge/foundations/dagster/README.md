---
name: dagster-foundation
description: "Use when building a workflow/DAG scheduler daemon: generator-driven daemon loops with heartbeat liveness, queued-run admission with priority+tag concurrency, cron catch-up windows, sensor/tick crash recovery, declarative-automation asset scheduling with versioned cursors, run monitoring timeout ladders, and auto-retry idempotence."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Dagster: Workflow Scheduler & Automation Daemon Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `dagster`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@4344eb7f4cf588c801c17489228790f002276aca`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Daemon core; Run queue; Run lifecycle; Schedules &
  sensors; Declarative automation; Backfills.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
