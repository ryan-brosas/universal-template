---
name: react-foundation
description: "Use when porting cooperative time-slicing schedulers, priority-ordered task queues, delayed-task timers, macrotask yield/error-resume loops, or lane/priority-bitmap scheduling kernels modeled on React's Scheduler (`packages/scheduler`) and the react-reconciler root-scheduling plane (`ReactFiberRootScheduler`, `ReactFiberWorkLoop` render entry, `ReactFiberLane`). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# React: Fiber scheduler foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `react`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@055705ca01766d2a4379261b05e7990a849bdedc`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Scheduler kernel (packages/scheduler); Heap ordering;
  Delayed tasks; Priorities & expiration; Continuations; Error resume; Host
  transport; Reconciler root-scheduling plane.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
