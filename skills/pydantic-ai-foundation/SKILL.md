---
name: pydantic-ai-foundation
description: "Use when porting or building an agent runtime's core machinery — deferred/external tool calls, human-in-the-loop approval, pause/resume envelopes, barrier-segmented parallel execution, structured-output schema resolution, capability middleware with ordering constraints, toolset composition (wrapper/combined/prefixed/renamed/prepared/filtered/dynamic/approval/external), streaming partial→final validation, the durable-execution shared kernel (string-only model round-trip with credential-leak rejection, replay-unit enqueue/cancel guards, live-vs-replay event-stream split), the durability-engine adapter plane (anyio-shielded cancel forwarding, boundary-guarded context rehydration, sequence-keyed cache keys, legacy-replay dual paths), static tool-choice deadlock gates, transport-level tenacity retries honoring Retry-After, session cancellation as typed resumable exceptions, and replayed-history hardening for partially-rejected provider turns. Source code and direct tests are ground truth."

kind: foundation
invocation: manual
disable-model-invocation: true
---
# pydantic-ai: Agent Runtime Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `pydantic-ai`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Deferred envelope; Step-final deferral ladder;
  Approval dispatch; End strategies; Parallel execution; Retry budget;
  Availability refusals; Declarative deferral.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
