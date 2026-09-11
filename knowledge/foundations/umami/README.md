---
name: umami-foundation
description: "Use when porting privacy-first analytics/telemetry machinery — cookieless derived session identity, rolling cache-token handshakes for anonymous ingest, dual-backend SQL dispatch (Postgres + ClickHouse), dynamic filter compilation with typed bind placeholders, Kafka wire-size batching, soft-delete read caches, 2FA with partial-auth tokens and replay ledgers, rrweb session-replay chunking/reassembly, heatmap capture with scroll bucketing, hand-rolled Core Web Vitals, and share-token capability grants."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# umami: privacy-first web analytics platform

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `umami`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `master@ca661c7057984aa98ed4f7083d84dae2f65bfcb0`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Identity & sessions; Auth & 2FA; Query engine; Ingest
  pipeline; Streaming infra; Tracker (browser); Session replay; Heatmap.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
