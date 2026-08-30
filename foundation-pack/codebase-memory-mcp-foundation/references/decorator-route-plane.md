<!-- capsule-v2 -->
# Decorator/HANDLES route plane — how do framework decorators become Route nodes joined to their handlers?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What phases turn `@app.get("/users")` into a Route node with a HANDLES edge — including incremental runs?

## Four-phase route builder
**Path/Symbol:** `src/pipeline/pass_route_nodes.c:cbm_pipeline_create_route_nodes` (1193–1231) + tests/test_edge_types_probe.c:296–560 (per-framework HANDLES contracts).
**Signature:** `void cbm_pipeline_create_route_nodes(cbm_gbuf_t *gb);`
**Data Shape:** Phase 1: visit HTTP_CALLS edges → mint `__route__METHOD__<canon>` nodes. Phase 2a: ensure decorator-tagged functions have Route+HANDLES (`ensure_decorator_routes` — needed because unchanged files don't re-extract in incremental mode). Phase 2b: connect prefix Routes to decorator handlers, then match infra Routes to handler Routes by URL path. Phase 3: DATA_FLOWS through matched routes. Phase 4/5: protobuf gRPC routes; SvelteKit filesystem routes.

### Decisive source
```c
/* Phase 2a: ensure all functions with route_path have Route+HANDLES.
 * Handles incremental mode where unchanged files don't re-extract. */
ensure_decorator_routes(gb);
/* Phase 2b: connect prefix Routes to decorator handler Functions.
 * Must run BEFORE match_infra_routes so infra matching can find
 * HANDLES edges on prefix Routes for the bridge. */
connect_prefix_to_decorators(gb);
match_infra_routes(gb);
create_data_flows(gb);
```

**Flow:** decorator extraction stamps route_path on handlers → ensure-phase materializes missing Route/HANDLES → prefix bridging (Laravel `Route::prefix()->group`) composes paths → infra route matching joins client HTTP_CALLS to handler routes via canonical path → data-flow edges close the loop.
**Invariant:** Phase ORDER is load-bearing (bridge before infra match); idempotence is required because incremental runs invoke this over partially-stale buffers.
**Probe:** `tests/test_edge_types_probe.c:handles_flask_python`, `handles_fastapi_python`, `handles_laravel_facade_routes_issue952` (+ its no-junk inverse), `tests/test_lang_contract.c:contract_edge_handles`, `contract_edge_data_flows`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_pipeline_create_route_nodes", limit: 5 });
```

## Verdict
Adopt phased/idempotent route materialization for any cross-service linking; adapt decorator tag extraction; omit SvelteKit/gRPC phases if out of scope.
