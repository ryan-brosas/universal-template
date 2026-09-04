---
name: sharex-foundation
description: Use when porting ShareX's desktop job kernel — per-task STA worker threads with UI-context event marshaling, bounded upload admission control, state-dependent stop/cancel ladders, retry ladders, after-upload pipelines, and uploader factory/config gates. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# ShareX: Task lifecycle kernel foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `sharex`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `develop@db2bba61232b957f3dfb6a69719d8cfbc7a80c2f`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Admission control; Task FSM / stop; Thread +
  marshaling; Cleanup contract; Retry; Post-upload chain; Uploader resolution;
  Recent items.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
