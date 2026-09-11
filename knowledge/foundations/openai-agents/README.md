---
name: openai-agents-foundation
description: "Use when building multi-agent frameworks: guardrail tripwires running parallel to generation, typed handoffs with history filtering, serializable human-in-the-loop run state, and the turn-resolution ladder that turns model output into action."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# OpenAI Agents Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `openai-agents`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@fe45b415`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Guardrails & handoffs; Turn engine; Run state & HITL;
  Turn loop & streaming; Session persistence; Model retry; Tools & approvals
  planning; Session stores & protocol.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
