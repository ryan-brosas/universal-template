---
name: uvicorn-foundation
description: "Use when porting an asyncio request-response server (HTTP/1.x, HTTP/2, WebSocket) or building the supervising shell around one — process lifecycle, graceful shutdown, worker fleets, protocol negotiation, backpressure, and proxy-trust boundaries. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Uvicorn: ASGI server kernel (lifecycle, supervision, protocol implementations)

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `uvicorn`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Lifecycle & supervision; Shutdown choreography; Max-
  requests jitter; Supervisor dispatch & import gate; Zero-downtime restart
  ladder; Signal-queue supervisor; Pipe healthcheck; Spawn bootstrap.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
