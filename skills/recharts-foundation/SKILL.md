---
name: recharts-foundation
description: 'Use when porting or reimplementing axis tick generation: nice-number step algorithms (adaptive/snap125), fixed vs extending domain strategies, value→pixel tick mapping with band offsets, collision-aware label filtering, categorical pixel inversion, and immutable d3-scale wrapping.'
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Recharts: chart scale & tick pipeline foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `recharts`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Step rounding; Nice snapping; Boundary search; Entry
  guards; Degenerate fan; Clamped generator; Precision substrate; Mode funnel.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
