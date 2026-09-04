---
name: openoats-foundation
description: "Use when porting a local-first recording/session store: canonical per-session directory layouts with permission-hardened atomic JSON writes, long-lived append file handles, delayed async-enrichment write draining before shutdown, destructive-overwrite backup ladders, time-windowed artifact retention, empty-\"ghost\" session reconciliation, abandoned-session resume election, user-tag updates that must preserve machine-namespaced tags, hostile-filename-safe attachment import with copy-before-metadata consistency, ordered finalize drain ladders with ghost collapse and typed recovery results, pure audio-retention/empty-session health plans, or session-selection state resets that preserve unsaved drafts. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# OpenOats: session-storage kernel foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `openoats`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@bc0ddb9d5d12e2ea4dddbc2c1b09e0c1ef708df7`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Session layout & seeding; Live handle lifecycle;
  Pending-write drain; Pre-batch backup ladder; Batch audio rerun window;
  Ghost reconciliation; Resume election; Internal-tag preservation.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
