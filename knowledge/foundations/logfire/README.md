---
name: logfire-foundation
description: "Use when porting logfire's OTel-native telemetry machinery: fail-soft span factories, disk-backed export reliability, scrubbing, tail sampling, managed variables."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# logfire: OTel-Native Observability SDK Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `logfire`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@e484a6b53a0df3062d304ce258573e387cf3140a`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Core span factories; Export reliability; Live-tail &
  sampling; Data quality; Error semantics; Configuration plane; Managed
  variables.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
