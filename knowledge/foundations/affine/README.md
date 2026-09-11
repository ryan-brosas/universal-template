---
name: affine-foundation
description: "Use when porting CRDT sync loops, offline-first storage ladders, or block-editor data layers — AFFiNE local-first collaboration stack: Yjs sync engine (DocEngine/SyncPeer), reactive block store (stash/pop, flat Y.Map proxies, schema globs), and production doc-sync job kernel with clock-map dedup."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# AFFiNE: local-first collaborative block editor

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `affine`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Sync engine (@blocksuite/sync); Reactive block store
  (@blocksuite/store); Production sync + server storage; Transformer / adapter
  plane (@blocksuite/store transformer + shared adapters).
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
