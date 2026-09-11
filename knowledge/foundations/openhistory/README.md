---
name: openhistory-foundation
description: "Use when porting append-only JSONL event-store ingestion, bounded record schemas, incremental append caches with partial-write recovery, atomic in-place file rewrites, stateful privacy/redaction filters over timestamp-ordered event streams, task-episode segmentation with stable derived-record ids, provenance reconciliation of derived summary stores after source deletions, or evidence- calibrated LLM summarization gates that cap claims at what observations prove. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# OpenHistory: local activity-history ingestion, projection & privacy foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `openhistory`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Parse gate; Fail-soft loader; Bounded dedup walk;
  Append cache; Atomic scrub; Sticky boundary filter; Segmentation ladder;
  Episode identity.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
