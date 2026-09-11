---
name: nexus-public-foundation
description: "Use when porting Nexus Repository infrastructure contracts: freeze-aware task scheduling over Quartz, thread-scoped transactions with retry/backoff semantics, the capability lifecycle framework for plugin objects, blob-store location/soft-delete/S3 multipart mechanics, JWT-cookie sessions, double-submit CSRF, sandboxed JEXL/CSEL content selectors with parameterized SQL push-down, the repository view handler chain, and the plugin/boot/UI-extension system (descriptors, lifecycle phases, edition selection, script gating, state polling)."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Nexus Repository Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `nexus-public`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@0a8a425daa4b37e924ca11e4637a41afce7b115c`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Task scheduling; Web security; Authorization core;
  Content selectors; Repository view pipeline; API layering; Transactional
  work units; Capability framework.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
