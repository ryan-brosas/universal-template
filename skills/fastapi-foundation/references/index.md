<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# FastAPI: Python ASGI web framework foundation

## Use this for
Use when porting FastAPI's request machinery — the dependency-injection solver and cache, signature-to-param classification, body/query validation, response dispatch and streaming (JSONL/SSE), lazy router composition with prefix/dependency inheritance, or OpenAPI schema generation — into another framework or service. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./dependency-solver-tree-walk.md` — how sub-dependencies are solved depth-first, error-short-circuited, and per-request cached.
- `./dependency-cache-identity.md` — the `(call, scopes, computed-scope)` cache key and when the same callable solves twice.
- `./param-analysis-ladder.md` — Annotated/default precedence deciding Query/Path/Body/File vs Depends vs special injection.
- `./dual-exit-stack-lifecycle.md` — function-scoped vs request-scoped yield-dep teardown ordering and the swallowed-exception detector.
- `./callable-classification-kernel.md` — identity-cached gen/coroutine/sync classification through partials, functors, classes.
- `./single-model-flattening.md` — lone BaseModel params expanding into per-field extraction with model-level error locs.
- `./body-embed-decision.md` — embed rule plus synthetic `Body_<op>` composite models for schema/media types.
- `./request-body-content-type-gate.md` — JSON-vs-bytes parsing gate and `json_invalid` 422 error synthesis.
- `./response-dispatch-dump-json-fast-path.md` — SSE→JSONL→generator→raw-Response→model precedence and Rust-core fast serialization.
- `./sse-keepalive-producer.md` — two-stage anyio pipeline keeping idle streams alive without cancelling user generators.
- `./lazy-included-router-composition.md` — include_router storing live router refs; version-keyed effective-context rebuilds.
- `./low-priority-frontend-routing.md` — SPA/static serving only after every API route misses, with dependencies on full matches.
- `./jsonable-encoder-ladder.md` — exact conversion order for arbitrary objects incl. custom encoders and `_sa` stripping.
- `./openapi-two-pass-assembly.md` — collect-fields-then-render pass structure, shared $refs, auto-422 suppression rules.
- `./defaultplaceholder-inheritance.md` — sentinel-wrapped defaults letting app/router defaults propagate without erasing explicit values.
- `./lifespan-merge-chain.md` — nested-lifespan composition semantics incl. state merge order and legacy event handlers.
- `./modelfield-typeadapter-adapter.md` — the Pydantic-v2 ModelField wrapper: errors-as-values, loc prefixes, identity hash.
- `./security-scope-inheritance.md` — cumulative OAuth scope computation feeding both runtime guards and OpenAPI requirements.
- `./stream-endpoint-typing.md` — generator return annotations deriving stream item schemas for JSONL/SSE.
- `./contextmanager-in-threadpool.md` — sync CM teardown on a private CapacityLimiter to avoid pool deadlocks.
- `./validation-exception-context.md` — endpoint file/line context attached to validation errors, cached per callable.
- `./openapi-schema-caching.md` — version-checked schema memoization plus root-path server injection.
- `./background-task-adoption-chain.md` — one lazily-created BackgroundTasks instance threaded from deps to post-send run.
- `./multipart-install-guard.md` — route-build-time detection of missing/wrong python-multipart.
- `./dependency-scope-rule.md` — why request-scoped generators cannot depend on function-scoped dependencies.

## Capsule map
- **Dependency solving** — `dependency-solver-tree-walk`: recursive solve with error short-circuit; `dependency-cache-identity`: tuple cache key; `callable-classification-kernel`: cached three-way classifier; `dependency-scope-rule`: build-time scope containment; `contextmanager-in-threadpool`: deadlock-free sync CM teardown.
- **Param & body validation** — `param-analysis-ladder`: classification precedence; `single-model-flattening`: model-as-params expansion; `body-embed-decision`: embed rule + Body_ synthesis; `request-body-content-type-gate`: strict content-type parsing.
- **Lifecycle** — `dual-exit-stack-lifecycle`: teardown ordering + latch guard; `lifespan-merge-chain`: lifespan/event composition.
- **Routing** — `lazy-included-router-composition`: version-keyed effective contexts; `low-priority-frontend-routing`: API-first static serving.
- **Responses & streaming** — `response-dispatch-dump-json-fast-path`: dispatch ladder + dump_json fast path; `sse-keepalive-producer`: keepalive pipeline; `stream-endpoint-typing`: annotation-derived item schemas; `background-task-adoption-chain`: post-send task hand-off.
- **Encoding & schema generation** — `jsonable-encoder-ladder`: recursive encoder fallbacks; `openapi-two-pass-assembly`: definitions-then-operations; `openapi-schema-caching`: memoized app.openapi(); `defaultplaceholder-inheritance`: Default() sentinel propagation.
- **Compat & diagnostics** — `modelfield-typeadapter-adapter`: v2 ModelField adapter; `validation-exception-context`: endpoint context capture; `security-scope-inheritance`: scope accumulation; `multipart-install-guard`: fail-fast form deps.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
FastAPI (MIT license), `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory project `ext-fastapi` (31,126 nodes / 74,859 edges, FULL-mode ready index at the pinned commit, parse_partial=0 skipped=0; all cited paths check_index_coverage `no_recorded_issue` + `metadata_match`; only `.git` and image suffixes excluded by design).

## Full view (memory graph)
Revalidate `ext-fastapi` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: dependant-tree solving with tuple-key caching, param-classification precedence, exit-stack teardown ordering, stream typing, encoder ladder, and the two-pass OpenAPI assembly — these transfer to any typed-request framework. Adapt host-specific integration: Starlette Request/Response/WebSocket plumbing, anyio memory-stream pipelines, threadpool execution choices, and the ASGI scope keys (`fastapi_inner_astack` etc.). Omit product surface behavior: Swagger/ReDoc HTML docs routes, the bundled docs UI assets, `fastapi dev` CLI, and tutorial/doc fixtures.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`background-task-adoption-chain.md`](./background-task-adoption-chain.md)
- [`body-embed-decision.md`](./body-embed-decision.md)
- [`callable-classification-kernel.md`](./callable-classification-kernel.md)
- [`contextmanager-in-threadpool.md`](./contextmanager-in-threadpool.md)
- [`defaultplaceholder-inheritance.md`](./defaultplaceholder-inheritance.md)
- [`dependency-cache-identity.md`](./dependency-cache-identity.md)
- [`dependency-scope-rule.md`](./dependency-scope-rule.md)
- [`dependency-solver-tree-walk.md`](./dependency-solver-tree-walk.md)
- [`dual-exit-stack-lifecycle.md`](./dual-exit-stack-lifecycle.md)
- [`jsonable-encoder-ladder.md`](./jsonable-encoder-ladder.md)
- [`lazy-included-router-composition.md`](./lazy-included-router-composition.md)
- [`lifespan-merge-chain.md`](./lifespan-merge-chain.md)
- [`low-priority-frontend-routing.md`](./low-priority-frontend-routing.md)
- [`modelfield-typeadapter-adapter.md`](./modelfield-typeadapter-adapter.md)
- [`multipart-install-guard.md`](./multipart-install-guard.md)
- [`openapi-schema-caching.md`](./openapi-schema-caching.md)
- [`openapi-two-pass-assembly.md`](./openapi-two-pass-assembly.md)
- [`param-analysis-ladder.md`](./param-analysis-ladder.md)
- [`request-body-content-type-gate.md`](./request-body-content-type-gate.md)
- [`response-dispatch-dump-json-fast-path.md`](./response-dispatch-dump-json-fast-path.md)
- [`security-scope-inheritance.md`](./security-scope-inheritance.md)
- [`single-model-flattening.md`](./single-model-flattening.md)
- [`sse-keepalive-producer.md`](./sse-keepalive-producer.md)
- [`stream-endpoint-typing.md`](./stream-endpoint-typing.md)
- [`validation-exception-context.md`](./validation-exception-context.md)
