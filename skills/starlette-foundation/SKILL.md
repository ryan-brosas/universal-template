---
name: starlette-foundation
description: "Use when porting Starlette's ASGI kernel — the router match loop and `{param:convertor}` path grammar, mount child-scope rewriting (`root_path`/`app_root_path`), lifespan state machine, exception-handler plumbing with response-started latching, `BaseHTTPMiddleware`'s memory-stream bridge, single-consumption request body/form contracts, multipart callback state machine, streaming disconnect ladder + Range/multipart-byteranges engine, WebSocket dual state machines, signed-cookie sessions, static-file containment, CORS preflight algebra, scope-data plane (ImmutableMultiDict/MultiDict/QueryParams/FormData repeated-key algebra, Headers first-match byte store vs MutableHeaders live-list kernel, lifespan↔request State write-through), URL construction/mutation plane (tri-form constructor with lazy SplitResult cache, replace() netloc reassembly with IPv6 guard), HTTPConnection derivation plane (identity-equality Mapping façade, snapshot memoization ladder, assert-guided session/auth/user facades, client Address)"
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Starlette: Python ASGI toolkit foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `starlette`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@675ae76855d3d09f5a4493c15ad321a3cd02390d`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Routing core; App lifecycle; Errors; HTTP middleware;
  Response plane; Data & URLs; Request plane; Realtime.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
