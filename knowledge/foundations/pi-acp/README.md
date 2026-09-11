---
name: pi-acp-foundation
description: "Use when building an Agent Client Protocol (ACP) adapter that bridges an external ACP client (JetBrains IntelliJ, Zed) to a single-session coding agent (pi): stdio NDJSON ACP server wiring, 1:1 session-to-subprocess mapping, pi RPC transport, turn state machine with agent_settled completion, monotonic tool-call statuses, ordered update emission, slash-command expansion, structured edit diffs, and an authenticated IPC bridge that exposes remote MCP tools as pi extension tools."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Pi-ACP-Jetbrain: ACP Adapter for a Single-Session Coding Agent

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `pi-acp`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: ACP server; Session mapping; Pi RPC transport; Turn
  state machine; Tool statuses; Edit diffs; Bash terminal; Slash commands.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
