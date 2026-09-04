<!-- capsule-v2 -->
# df-payload-acquisition-ladder — How does one chart query acquire its dataframe payload without caching failures or leaking timing into payloads?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** What is the exact ordered contract for acquiring a query's dataframe, and which steps must happen before the cache key exists?

## QueryContextProcessor.get_df_payload_result
**Path/Symbol:** `superset/common/query_context_processor.py:97-265` (`get_df_payload_result`; thin facade `get_df_payload` :91-95 returns only `.payload`).
**Signature:** `def get_df_payload_result(self, query_obj: QueryObject, force_cached: bool | None = False) -> QueryAcquisitionResult`
**Data Shape:** Input `QueryObject` (may be falsy); output frozen dataclass `QueryAcquisitionResult(payload: dict, timing: QueryAcquisitionTiming)` where payload carries `cache_key/cached_dttm/queried_dttm/cache_timeout/df/applied_template_filters/applied_filter_columns/rejected_filter_columns/annotation_data/error/is_cached/query/status/stacktrace/rowcount/sql_rowcount/from_dttm/to_dttm/label_map/warning`.

### Decisive source
```python
if query_obj:
    # Always validate the query object before generating cache key
    # This ensures sanitize_clause() is called and extras are normalized
    query_obj.validate()

cache_key = self.query_cache_key(query_obj)
timeout = self.get_cache_timeout()
force_query = self._query_context.force or timeout == CACHE_DISABLED_TIMEOUT
...
cache = QueryCacheManager.get(key=cache_key, region=CacheRegion.DATA,
    force_query=force_query, force_cached=force_cached)

# If cache is loaded but missing applied_filter_columns and query has filters,
# treat as cache miss to ensure fresh query with proper applied_filter_columns
if (query_obj and cache_key and cache.is_loaded and not cache.applied_filter_columns
        and query_obj.filter and len(query_obj.filter) > 0):
    cache.is_loaded = False
```

**Flow:** (1) `query_obj.validate()` — strictly BEFORE key generation so `sanitize_clause()` normalizes extras; (2) compute `cache_key` + `timeout`; (3) `force_query = context.force or timeout == CACHE_DISABLED_TIMEOUT`; (4) resolve cache; (5) stale-shape downgrade (own capsule); (6) on miss: invalid-column pre-check raises `QueryObjectValidationError` → recorded as `cache.error_message` + `status=FAILED` **without** `set_query_result`; success runs `get_query_result` + `get_annotation_data`, then caches; (7) rebuild `label_map` by un-escaping the flattened-frame comma escape (`unescape_separator` + `re.split(r"(?<!\\),\s", col)`), overlaying column/metric name maps incl. adhoc SQL expressions; (8) BigQuery memory-limit warning prefixed with `slice_id` when present; (9) assemble payload dict and a four-phase `QueryAcquisitionTiming` (`perf_counter_ns` deltas, clamped `max(0, …)`).

**Invariant:** Validation precedes key computation; a failed acquisition mutates the in-memory cache object but never writes a cache entry; timing values stay out of the payload dict and travel in the typed sidecar.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:1518` (`test_get_df_payload_validates_before_cache_key_generation`) pins validate-before-key ordering; `tests/unit_tests/common/test_query_context_processor_timing.py:177` pins the demotion happening inside the timed `cache_resolution` window.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "get_df_payload_result acquisition timing payload", limit: 10 });
```

## Verdict
Adopt the ladder order (validate → key → timeout/force → resolve → acquire → cache-only-on-success → assemble) and the sidecar-timing separation; adapt `CACHE_DISABLED_TIMEOUT`, Flask i18n `_()`, and pandas label plumbing to your host; omit Superset's specific payload field set if your transport differs. Coverage: all cited ranges read directly at pin; file `no_recorded_issue`.
