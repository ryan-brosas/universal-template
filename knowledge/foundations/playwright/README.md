---
name: playwright-foundation
description: "Use when porting Playwright's client RPC architecture (GUID object trees, channel proxies, async emitters, Waiter/Progress cancellation, timeout ladders, typed error round-trips) or its child-process lifecycle kernel (spawn fd layout, graceful-close ladders, signal refcounting, cross-platform tree kill, length-prefixed pipe framing, launch readiness races)."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Playwright (microsoft/playwright): Client RPC & Cancellation Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `playwright`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Message dispatch; Object lifecycle; Channel surface;
  Async context; Event plumbing; Lazy subscriptions; Wait orchestration;
  Server cancellation.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
