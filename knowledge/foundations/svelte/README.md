---
name: svelte-foundation
description: "Use when porting or reimplementing a push-mark/pull-verify signals runtime, a batched effect scheduler (microtask flush with synchronous escape), lazy derived caching with version counters, concurrent \"time-travelling\" async batches, a linked-list effect tree with pause/resume branch semantics, or the consumption planes over them — prop accessor factories with spread/rest proxies, store-to-signal subscription bridges, await-block flatten/context-save suspension, derived-owned effect freeze/unfreeze, and keyed-each single-pass reconciliation — as proven by svelte's client runtime (`packages/svelte/src/internal/client/{reactivity,runtime.js,dom/blocks}`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Svelte: signals runtime & reactivity kernel foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `svelte`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Write path; Flush machine; Root scheduling; Time
  travel; Derived pull; Effect tree; Props; Stores.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
