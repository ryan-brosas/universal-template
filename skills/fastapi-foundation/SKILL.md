---
name: fastapi-foundation
description: "Use when porting FastAPI's request machinery (Python ASGI web framework) — the dependency-injection solver and cache, signature-to-param classification, body/query validation, response dispatch and streaming (JSONL/SSE), lazy router composition with prefix/dependency inheritance, or OpenAPI schema generation — into another framework or service. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# FastAPI: Python ASGI web framework foundation

## Use this for
Use when porting FastAPI's request machinery — the dependency-injection solver and cache, signature-to-param classification, body/query validation, response dispatch and streaming (JSONL/SSE), lazy router composition with prefix/dependency inheritance, or OpenAPI schema generation — into another framework or service. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/dependency-solver-tree-walk.md` — how sub-dependencies are solved depth-first, error-short-circuited, and per-request cached.
- `references/dependency-cache-identity.md` — the `(call, scopes, computed-scope)` cache key and when the same callable solves twice.
- `references/param-analysis-ladder.md` — Annotated/default precedence deciding Query/Path/Body/File vs Depends vs special injection.
- `references/dual-exit-stack-lifecycle.md` — function-scoped vs request-scoped yield-dep teardown ordering and the swallowed-exception detector.
- `references/callable-classification-kernel.md` — identity-cached gen/coroutine/sync classification through partials, functors, classes.
- `references/single-model-flattening.md` — lone BaseModel params expanding into per-field extraction with model-level error locs.
- `references/body-embed-decision.md` — embed rule plus synthetic `Body_<op>` composite models for schema/media types.
- `references/request-body-content-type-gate.md` — JSON-vs-bytes parsing gate and `json_invalid` 422 error synthesis.
- `references/response-dispatch-dump-json-fast-path.md` — SSE→JSONL→generator→raw-Response→model precedence and Rust-core fast serialization.
- `references/sse-keepalive-producer.md` — two-stage anyio pipeline keeping idle streams alive without cancelling user generators.
- `references/lazy-included-router-composition.md` — include_router storing live router refs; version-keyed effective-context rebuilds.
- `references/low-priority-frontend-routing.md` — SPA/static serving only after every API route misses, with dependencies on full matches.
- `references/jsonable-encoder-ladder.md` — exact conversion order for arbitrary objects incl. custom encoders and `_sa` stripping.
- `references/openapi-two-pass-assembly.md` — collect-fields-then-render pass structure, shared $refs, auto-422 suppression rules.
- `references/defaultplaceholder-inheritance.md` — sentinel-wrapped defaults letting app/router defaults propagate without erasing explicit values.
- `references/lifespan-merge-chain.md` — nested-lifespan composition semantics incl. state merge order and legacy event handlers.
- `references/modelfield-typeadapter-adapter.md` — the Pydantic-v2 ModelField wrapper: errors-as-values, loc prefixes, identity hash.
- `references/security-scope-inheritance.md` — cumulative OAuth scope computation feeding both runtime guards and OpenAPI requirements.
- `references/stream-endpoint-typing.md` — generator return annotations deriving stream item schemas for JSONL/SSE.
- `references/contextmanager-in-threadpool.md` — sync CM teardown on a private CapacityLimiter to avoid pool deadlocks.
- `references/validation-exception-context.md` — endpoint file/line context attached to validation errors, cached per callable.
- `references/openapi-schema-caching.md` — version-checked schema memoization plus root-path server injection.
- `references/background-task-adoption-chain.md` — one lazily-created BackgroundTasks instance threaded from deps to post-send run.
- `references/multipart-install-guard.md` — route-build-time detection of missing/wrong python-multipart.
- `references/dependency-scope-rule.md` — why request-scoped generators cannot depend on function-scoped dependencies.

## Capsule map
- **Dependency solving** — `dependency-solver-tree-walk`: recursive solve with error short-circuit; `dependency-cache-identity`: tuple cache key; `callable-classification-kernel`: cached three-way classifier; `dependency-scope-rule`: build-time scope containment; `contextmanager-in-threadpool`: deadlock-free sync CM teardown.
- **Param & body validation** — `param-analysis-ladder`: classification precedence; `single-model-flattening`: model-as-params expansion; `body-embed-decision`: embed rule + Body_ synthesis; `request-body-content-type-gate`: strict content-type parsing.
- **Lifecycle** — `dual-exit-stack-lifecycle`: teardown ordering + latch guard; `lifespan-merge-chain`: lifespan/event composition.
- **Routing** — `lazy-included-router-composition`: version-keyed effective contexts; `low-priority-frontend-routing`: API-first static serving.
- **Responses & streaming** — `response-dispatch-dump-json-fast-path`: dispatch ladder + dump_json fast path; `sse-keepalive-producer`: keepalive pipeline; `stream-endpoint-typing`: annotation-derived item schemas; `background-task-adoption-chain`: post-send task hand-off.
- **Encoding & schema generation** — `jsonable-encoder-ladder`: recursive encoder fallbacks; `openapi-two-pass-assembly`: definitions-then-operations; `openapi-schema-caching`: memoized app.openapi(); `defaultplaceholder-inheritance`: Default() sentinel propagation.
- **Compat & diagnostics** — `modelfield-typeadapter-adapter`: v2 ModelField adapter; `validation-exception-context`: endpoint context capture; `security-scope-inheritance`: scope accumulation; `multipart-install-guard`: fail-fast form deps.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
FastAPI (MIT license), `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory project `ext-fastapi` (31,126 nodes / 74,859 edges, FULL-mode ready index at the pinned commit, parse_partial=0 skipped=0; all cited paths check_index_coverage `no_recorded_issue` + `metadata_match`; only `.git` and image suffixes excluded by design).

## Full view (memory graph)
Revalidate `ext-fastapi` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: dependant-tree solving with tuple-key caching, param-classification precedence, exit-stack teardown ordering, stream typing, encoder ladder, and the two-pass OpenAPI assembly — these transfer to any typed-request framework. Adapt host-specific integration: Starlette Request/Response/WebSocket plumbing, anyio memory-stream pipelines, threadpool execution choices, and the ASGI scope keys (`fastapi_inner_astack` etc.). Omit product surface behavior: Swagger/ReDoc HTML docs routes, the bundled docs UI assets, `fastapi dev` CLI, and tutorial/doc fixtures.
