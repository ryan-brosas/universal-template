---
name: healthchecks-foundation
description: "Use when building a dead-man's-switch heartbeat monitor or cron-watchdog service: grace-deadline state machines across simple/cron/OnCalendar schedules, alert_after partial-index polling, ping ingest transactions with run-ID duration matching, flip outboxes, DB token-bucket rate limiting with an S3 circuit breaker, inverted-prefix S3 pruning, SSRF-guarded egress, signed bounce ingestion, and uwsgi attach-daemon deployment."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# healthchecks: Heartbeat Watchdog Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `healthchecks`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@29b5ec251059034b79e0120e2ff0c3e35d7bd9f8`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Deadline engine; Signal intake; Scheduler workers;
  Outbox & fan-out; Integration transports; Accounts & abuse control;
  Statistics & retention; Deployment.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
