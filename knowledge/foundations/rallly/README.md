---
name: rallly-foundation
description: "Use when porting group-scheduling poll machinery — floating vs timezone-pinned option storage, auto-close/reopen ladders, guest edit-token authorization, vote aggregation and scoring, atomic booking with invite dedup, cron housekeeping (inactivity retention + purge), or per-recipient email rendering."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Rallly: scheduling-poll foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `rallly`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Option encoding; Event booking times; Close/reopen
  ladder; Inactivity retention; Soft-delete invisibility; Guest token actors;
  Participant visibility; Score formula.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
