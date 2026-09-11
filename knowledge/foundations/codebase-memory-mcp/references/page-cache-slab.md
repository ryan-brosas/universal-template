<!-- capsule-v2 -->
# Shared page-cache slab — how do you stop short-lived read connections from pinning allocator pages?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When per-request SQLite connections fragment your allocator, what one-time fix makes page-cache memory dense and bounded?

## Contiguous slab for SQLite page cache, installed once on first open
**Path/Symbol:** `src/store/store.c` — "Shared page-cache slab" block (755–775).
**Signature:** embedded in `cbm_store_open_memory()` / first `store_open_internal`; must run BEFORE SQLite initialises.
**Data Shape:** Diagnosis (#581, native Windows): request-scoped READONLY stores drew page cache from the general allocator; survivors pinned 512 KiB MEDIUM-class pages — 140 pages ≈1.4 MiB live at ~2% occupancy that no purge could reclaim (pages in use, not free). Fix: hand SQLite ONE contiguous slab reused across connections.

### Decisive source
```c
/* Every request opens its own short-lived read-only store, and SQLite serves
 * that connection's page cache from the general allocator. Measured on native
 * Windows ... a handful of survivors pin a 512 KiB page each — 140 pages held
 * ~1.4 MiB of live data, roughly 2% occupancy, which no purge can reclaim
 * because the pages are in use rather than free.
 * Giving SQLite one contiguous slab to serve page cache from makes that memory
 * dense and bounded, and — because the slab is reused across connections —
 * removes the per-request churn that did the pinning. */
```

**Flow:** first store open installs the slab → every subsequent connection's page cache draws from it → fixed upfront commit replaces unbounded churn → arena census confirms zero free-committed drift elsewhere.
**Invariant:** Install order (before sqlite init) is mandatory; the win is bounded density + churn removal, not raw size reduction.
**Probe:** allocation-shape evidence via mem suite arena census (`tests/test_mem.c:mem_collect_reclaims`, `mem_rss_tracking`) and diagnostics stats files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "page-cache slab", limit: 5 });
```

## Verdict
Adopt dedicated slabs for subsystems with pathological size-class mixing; adapt slab sizing to measured working sets; omit if your connections are long-lived (no churn to fix).
