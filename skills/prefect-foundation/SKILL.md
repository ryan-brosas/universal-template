---
name: prefect-foundation
description: Use when building or porting workflow engines - heartbeat liveness past blocked loops, termination-intent dispatch, cancellation ownership across process boundaries, subflow reattach ladders, client-side retry/backoff arithmetic, transactional result caching, crash taxonomies, and supervised-process exit contracts - plus fire-and-forget telemetry batching (singleton queue services on a global loop, byte-budget log upload, context-capturing event workers, websocket resend with checkpoint acks) and event-driven completion waiting (subscriber replay backfill windows, seen-id dedup, clean-vs-abnormal close policy, register-recheck waiter ladders, terminal-event fan-in singletons, heartbeat backoff loops), lossy-tolerant log-stream consumption, dual-stream queue fan-in with sentinel/straggler-drain termination, recency-cached lineage enrichment, and thread-keyed sync/async waiter primitives - capsule-v2 source maps with decisive excerpts and graph retrieval.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# prefect: workflow-engine foundations

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `prefect`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Liveness; Termination plane; Resumability; Process
  boundary; Execution shells; Run records; Retry plane; State ledger.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
