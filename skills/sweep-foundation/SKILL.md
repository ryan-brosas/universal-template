---
name: sweep-foundation
description: "Use when porting GitHub-app webhook routers that fan out to long-running agent jobs: fail-open HMAC signature gates, latest-wins ctypes thread cancellation, per-object coalescing work queues, event/action gate ladders, GHA-autofix attribution chains, single-progress-comment lifecycles, branch/commit/PR assembly, cron PR maintenance, delta-gated progress persistence, mutable-comment header rendering, lexical/vector code-search infrastructure, LLM file-selection budgeting, Jira second-forge dispatch via issue mirroring, FCR tag grammar with COPIED_FROM markers, FCR application loops with lazy tool calls, self-correcting search-and-replace match ladders, FCR pre-validation escape hatches, GHA two-stage planner, repo-parsing chunk corpus builder, lint/parse validation kernel, FCR tag grammar kernel, jsonpatch-diffed chat streaming, stateful suggestion streaming, XML tool-call parse twins, and plan-context assembly. Source/tests ground truth; references carry excerpts."
kind: foundation
invocation: manual
disable-model-invocation: true
---
# sweep: GitHub webhook dispatch & ticket lifecycle foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `sweep`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@a8b8b67bda4f89faac9314d34e7c7d5a64f76046`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Webhook entry contract; Latest-wins threads;
  Coalescing priority queue; Event-router gate ladder; GHA autofix
  attribution; Progress-comment lifecycle; Branch/commit/PR ladder; Ticket
  ledger write path.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
