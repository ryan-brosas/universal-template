<!-- capsule-v2 -->
# get_architecture aspects — how do you serve layered architecture views (boundaries, hotspots, clusters) from raw edges?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What aspect vocabulary turns CALLS edges into boundary/hotspot/layers/file-tree/clusters views?

## Aspect-array API with per-aspect rollups
**Path/Symbol:** `src/store/store.h:761–764` + engine in store.c (~7300s) + tests/test_store_arch.c:143–560.
**Signature:** `int cbm_store_get_architecture(cbm_store_t *s, const char *project, const char *path, const char **aspects, int aspect_count, cbm_architecture_info_t *out);`
**Data Shape:** Aspects: all / boundaries (server→handler→service layer transitions), entry_points (+exclude-tests variant), hotspots (degree-ranked, exclude_tests flag), languages, routes, layers, file_tree, clusters; path param scopes to a subdirectory; output struct has per-aspect arrays with counts.

### Decisive source
```c
TEST(arch_boundaries) {
    ... const char *aspects[] = {"boundaries"};
    ASSERT_EQ(cbm_store_get_architecture(s, "test", NULL, aspects, 1, &info), CBM_STORE_OK);
    /* server → handler and handler → service should be present */
```
```c
TEST(arch_boundaries_no_quadratic_scan) { ... }  /* perf-pinned via timed_boundaries_ms */
```

**Flow:** resolve project/path scope → run only requested aspects → boundaries derive from cross-directory CALLS chains → hotspots rank by degree (tests excluded on request) → clusters group by connectivity → free via cbm_store_architecture_free.
**Invariant:** Aspect selection must be additive and independent — requesting one aspect must not change another's numbers; the no-quadratic-scan pin keeps boundaries linear-ish at scale.
**Probe:** `arch_all`, `arch_entry_points_exclude_tests`, `arch_hotspots`, `arch_layers`, `arch_clusters` in tests/test_store_arch.c.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_architecture", limit: 5 });
```

## Verdict
Adopt aspect-parameterized architecture rollups over raw edge data; adapt your aspect list; keep the perf pin for any graph-derived summary.
