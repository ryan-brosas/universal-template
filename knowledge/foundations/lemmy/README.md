---
name: lemmy-foundation
description: "Use when building federation/dispatch engines: per-peer DB-backed activity queues with exactly-once cursors, exponential backoff shared across concurrent senders, modulo-sharded worker fleets, community inbox fan-out maps, Announce wrapping, signed inbound receive gates with dedup, and cross-vendor object round-trips."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Lemmy: federation protocol & dispatch engine

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `lemmy`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@439734dd638a2c06a2f907beab7dcf4646e88f86`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Send queue; Failure policy; Fan-out map; Scale-out;
  Peer lifecycle; Durable hand-off; Routing; Broadcast envelope.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
