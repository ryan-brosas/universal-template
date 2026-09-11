---
name: openai-swarm-foundation
description: "Use when porting or building a minimal agent runtime (tool-call loop, agent handoffs, shared context), designing a triage/router multi-agent topology, generating OpenAI tools schemas from Python functions, reassembling streamed chat-completion deltas, or testing agent loops without a live model. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# openai-swarm: minimal-agent foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `openai-swarm`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Run loop; Handoffs; Shared memory; Tool execution;
  Schema generation; Stream assembly; Streaming surface; Data model.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
