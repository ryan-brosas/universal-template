---
name: langgraph-foundation
description: "Use when building agent orchestration engines, step graphs, or durable resumable runtimes — reusable contracts from LangGraph (MIT): the Pregel execution kernel — channel semantics (LastValue/Topic/BinOp/Ephemeral/Barrier/Delta), BSP superstep loop with version-based triggering, deterministic task IDs, interrupt/resume scratchpad protocol, runner panic/cancel semantics, retry ladder with ParentCommand routing, durability modes, exit-mode delta persistence, stream-mode output projection with custom-writer injection, branch/Command navigation grammar, Send fan-out guards, per-node input projection, managed values, functional-API call reuse on resume, messages-mode callback propagation (incl. v2 content-block streaming), subgraph checkpoint addressing, write caching, idle-timeout guards with attempt-observer contract, parent-config checkpoint chains, and runtime override/merge algebra."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# LangGraph: Pregel Execution Kernel Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `langgraph`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Driver loop; State semantics; Triggering; Identity;
  HITL; Replay; Orchestration; Failure routing.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
