---
name: vue-core-foundation
description: "Use when porting or building a proxy-based fine-grained reactivity kernel: Dep/Link dependency graph, pull-based computed ladder, effect lifecycle & scope disposal, reactive/readonly/collection proxies, array instrumentations, trigger fan-out, refs, and base watch."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Vue Core (@vue/reactivity): Proxy Reactivity Kernel Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `vue-core`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@e2bede96134f757aad5c5b33ac9be055022dbfc8`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Dependency graph; Notification queue; Effect runner;
  Computed cache; Scope disposal; Proxy traps; Proxy factory; Collections.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
