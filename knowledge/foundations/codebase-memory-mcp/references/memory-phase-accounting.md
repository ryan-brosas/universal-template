<!-- capsule-v2 -->
# Memory phase accounting — how do you attribute memory growth to a request instead of guessing?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do phase marks bracket a request so a leak is attributable to a POOL rather than inferred from process totals?

## request.scope_begin/scope_end/idle marks + post-release census
**Path/Symbol:** `src/mcp/mcp.c:cbm_mcp_handle_tool` (11460–11487) + `src/foundation/mem.{h,c}:cbm_mem_phase_mark` (721+) and `cbm_mem_census_log`.
**Signature:** `void cbm_mem_phase_mark(const char *label);` — off unless `CBM_MEM_PHASES=1`, hot path pays one atomic load.
**Data Shape:** Marks: `request.scope_begin` → `request.dispatch_tool` → `request.scope_end` → `request.release_store` → `idle`. One census per completed request emitted AFTER the store release — the point where a well-behaved request has given everything back.

### Decisive source
```c
/* Phase marks bracket the WHOLE request with no unlabelled gap, so growth
 * cannot hide between them ... The "idle" label owns everything outside a
 * request, which is what makes a request-path retainer distinguishable from
 * background growth. */
...
/* One census per completed request, so growth can be attributed to a POOL
 * rather than inferred from a process total (#581). Emitted after the request
 * store is released ... */
cbm_mem_census_log("mcp.request");
```

**Flow:** enter handler → mark scope_begin → dispatch → scope_end → release per-request store → census log attributes committed bytes to the open label → back to idle. Cancellation-scope failure path marks idle too.
**Invariant:** NO unlabelled gaps inside a request; the census must run after releases or it measures retention that isn't the request's fault.
**Probe:** exercised via mem suite (`tests/test_mem.c:mem_rss_tracking`, `mem_collect_reclaims`) plus diagnostics soak; production wiring pinned by the handle_tool flow above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_mem_phase_mark", limit: 5 });
```

## Verdict
Adopt gapless phase marking + post-release census for any long-lived server chasing leaks; adapt labels; keep the env gate so production pays ~nothing.
