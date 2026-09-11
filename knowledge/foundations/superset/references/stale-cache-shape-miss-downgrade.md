<!-- capsule-v2 -->
# stale-cache-shape-miss-downgrade — When must an already-loaded cache entry be deliberately demoted to a cache miss?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** How does the acquisition ladder protect against legacy/partially-shaped cached entries that cannot answer a filtered request correctly?

## Loaded-cache compatibility policy
**Path/Symbol:** `superset/common/query_context_processor.py:131-139` (inside `get_df_payload_result`).
**Signature:** inline predicate on `QueryCacheManager` state + `query_obj.filter`.
**Data Shape:** `cache.applied_filter_columns: list[Column]` (empty list is the "old shape" signal); `query_obj.filter: list` of applied filters.

### Decisive source
```python
# If cache is loaded but missing applied_filter_columns and query has filters,
# treat as cache miss to ensure fresh query with proper applied_filter_columns
if (
    query_obj
    and cache_key
    and cache.is_loaded
    and not cache.applied_filter_columns
    and query_obj.filter
    and len(query_obj.filter) > 0
):
    cache.is_loaded = False
```

**Flow:** cache hit loads → shape probe: if the entry predates `applied_filter_columns` tracking (empty list) AND this request actually carries filters → flip `is_loaded=False` so stage 6 of the ladder runs a live query and re-caches a complete-shaped entry. The demotion occurs inside the timed `cache_resolution` window; the subsequent live acquisition is timed as `data_acquisition_ns`.
**Invariant:** A loaded-but-incompatible entry never reaches the caller as `is_cached=True` data when filters are present; compatibility is judged by *shape*, not by entry age or version markers.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:1974-2041` (`test_get_df_payload_invalidates_cache_missing_applied_filter_columns`) builds a loaded MockCache with `applied_filter_columns=[]` + a filtered QueryObject and asserts `mock_cache.is_loaded is False` after `get_df_payload`; `tests/unit_tests/common/test_query_context_processor_timing.py:177-227` additionally pins the demotion happening inside the timed `cache_resolution` window with `set_query_result` called once afterwards.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "applied_filter_columns cache miss downgrade loaded", limit: 10 });
```

## Verdict
Adopt shape-based compatibility demotion for any cached record whose schema grew new required fields; adapt the specific field name to your cache value contract; omit Superset's exact timing instrumentation if you have none. Coverage: source range read directly; direct test read at :177-227; file `no_recorded_issue`.
