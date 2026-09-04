---
name: flask-foundation
description: "Use when porting Flask's micro-framework (WSGI request lifecycle) — blueprint registration, session/cookie machinery, config loading, or context/proxy architecture — into another framework or a WSGI-compatible reimplementation. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Flask: micro-framework foundation (WSGI request lifecycle)

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `flask`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@d318b683471101618febed18996405ad26462110`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Context kernel; WSGI pipeline; Routing surface;
  Blueprint system; Hooks & errors; Streaming & background; State &
  serialization; Templates.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
