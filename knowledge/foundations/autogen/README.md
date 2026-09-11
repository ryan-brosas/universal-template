---
name: autogen-foundation
description: "Use when porting multi-agent orchestration machinery from Microsoft AutoGen (Python): single-queue envelope runtime, topic/subscription message bus, intervention hooks at dequeue time, group-chat supervisor loops (round-robin, LLM selector, swarm handoff, DAG graph flow), FIFO ordered delivery, termination algebra, run/stream lifecycle, bounded agent tool-call loops, RPC cancellation/failure ladders, name-keyed team checkpointing, middle-out token-budget contexts, mutate-and-report memory injection, subprocess executor timeout/cancel exit codes, grpc worker/host registration handshake with request-id correlation and disconnect cleanup, streamed tool-call workbenches, and pluggable model-context recall strategies."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# AutoGen: Agent Runtime & Group-Chat Foundations

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `autogen`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Envelope dispatch; Interventions; Fan-out;
  Instantiation; Routing; Subscriptions; Subscription registry; Serialization.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
