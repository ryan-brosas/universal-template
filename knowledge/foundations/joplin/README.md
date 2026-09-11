---
name: joplin-foundation
description: 'Use when porting joplin''s offline-first sync kernel: TTL lock election over dumb targets, timestamp-LWW sync-info merges, three-step sync choreography with failsafes, conflict triage ordering, and the sync-target transport plane (backend registry, FileApi adapter contract, transport retry ladder, remote-clock offset probe, two-tier driver delta).'
kind: foundation
invocation: manual
disable-model-invocation: true
---
# joplin: offline-first sync kernel

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `joplin`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Lifecycle; Mutual exclusion (dormant); Target state
  plane; Outgoing changes; Incoming changes; Deletion & conflict; Failure
  surface; Transport & adaptation plane.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
