---
name: shadcn-ui-foundation
description: Use when porting shadcn/ui's CLI registry-client machinery — typed registry error taxonomy with server-detail extraction, promise-in-flight fetch cache keyed by URL+header hash, AsyncLocalStorage registry header/env context, namespaced @registry URL building with {name}/{style}/${VAR} templating and env-var header suppression, item-address scheme dispatch (url/file/namespace/github/shadcn), recursive dependency-tree resolution with source tracking and fail-loud namespace errors, Kahn topological sort over name::source-hash node ids, proxy-aware manual-redirect fetching that strips secrets on cross-origin hops, anonymous-lock GitHub auth ladders with single-flight credential selection, sanitized transport-error taxonomy for subprocess+REST fleets, hermetic gh slot semaphores, streaming oversize read caps, git ls-remote ref-resolution ladders with authenticated fallbacks, rejection-evicting per-invocation source caches, and bounded-concurrency validation sweeps.
kind: foundation
invocation: manual
disable-model-invocation: true
---
# shadcn/ui: Registry Client Plane Foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `shadcn-ui`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Registry error taxonomy; Fetch promise cache;
  Registry ALS context; Namespaced URL builder; Item address dispatch;
  Dependency tree walk; Topological source-hash sort; Proxy fetch + origin-
  scoped redirects.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
