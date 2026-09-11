---
name: celery-foundation
description: "Use when building a distributed task queue or job worker: at-least-once ack/reject semantics across early/late modes, retry ladders (manual Task.retry, autoretry wrapper, exponential backoff with full jitter), prefork pool with event-loop time limits, bootstep blueprint startup/shutdown graphs, broker reconnect loops, ETA/countdown timers, beat's reentrant heap scheduler with crontab DST math, gossip worker elections, and mailbox-based remote control."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Celery: Distributed Task Queue Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `celery`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Execution spine; Retry & timeouts; Pool; Boot &
  connect; Heartbeat & gossip; Beat scheduling; Results & control; Producer &
  cluster.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
