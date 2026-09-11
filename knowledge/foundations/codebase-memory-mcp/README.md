---
name: codebase-memory-mcp-foundation
description: "Use when porting codebase-memory-mcp's C internals: SQLite graph store pragmas/integrity/quarantine, atomic publish pipeline, incremental closure routing, MCP server surface (TOON, profiles, cancellation), daemon rendezvous/version-cohort IPC, watcher/supervisor resilience, or the foundation allocator/lock/log primitives."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# codebase-memory-mcp: code-graph engine — store, pipeline, MCP, and daemon kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `codebase-memory-mcp`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Store open & integrity; Nodes & queries; Publish
  pipeline; Incremental & passes; MCP surface; Agent integration; Daemon
  coordination; Extraction passes.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
