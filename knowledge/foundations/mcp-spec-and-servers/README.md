---
name: mcp-spec-and-servers-foundation
description: "Use when building MCP servers or clients: modern-era stateless lifecycle, per-request _meta, Streamable HTTP + stdio transports, MRTR, subscriptions, OAuth 2.1 authorization, resource/prompt/completion surfaces, client features (elicitation/sampling/roots), dual-era dispatch, the Tasks extension plus task-based tool authoring and bidirectional task clients, cancellation/progress/ping patterns, structured tool outputs, URL-elicitation error paths, bounded fetches, and canonical reference-server patterns."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# MCP Spec & Servers Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `mcp-spec-and-servers`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Protocol core; Error routing & state; Transports;
  Extension & header surfaces; Interaction patterns; Data surfaces;
  Authorization (HTTP transports); Server↔client features.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
