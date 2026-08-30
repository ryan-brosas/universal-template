<!-- capsule-v2 -->
# query-cache-manager-fault-tolerance — How does the query cache behave under backend outage, forced-cache misses, and failed acquisitions?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** Which failures degrade to "cache miss", which raise, and what exactly gates a cache write?

## QueryCacheManager
**Path/Symbol:** `superset/common/utils/query_cache_manager.py:45-266` (whole class read; `get` :165-237, `set_query_result` :93-163, region map :39-42).
**Signature:** `QueryCacheManager.get(cls, key, region=CacheRegion.DEFAULT, force_query=False, force_cached=False) -> QueryCacheManager`; `set_query_result(self, key, query_result, annotation_data=None, force_query=False, timeout=None, datasource_uid=None, region=...) -> None`
**Data Shape:** Region-keyed Flask-Caching instances `{DEFAULT: cache, DATA: data_cache}`; cached value dict carries `df/query/applied_template_filters/applied_filter_columns/rejected_filter_columns/annotation_data/sql_rowcount/queried_dttm/dttm/bq_memory_limited/bq_memory_limited_row_count`.

### Decisive source (read outage ⇒ miss)
```python
try:
    cache_value = _cache[region].get(key)
except Exception as ex:  # pylint: disable=broad-except
    # A cache backend outage (e.g. Redis connection/timeout errors)
    # should not surface as an error to the caller: treat it the
    # same as a cache miss and fall through to querying live data.
    logger.warning("Error reading cache: %s", error_msg_from_exception(ex))
    cache_value = None
...
if force_cached and not query_cache.is_loaded:
    logger.warning("force_cached (QueryContext): value not found for key %s", key)
    raise CacheLoadError("Error loading data from cache")
```

### Decisive source (write gating + request-scoped flags)
```python
if self.status != QueryStatus.FAILED:
    ...self.is_loaded = True
if has_request_context():
    self.bq_memory_limited = getattr(g, "bq_memory_limited", False)
    self.bq_memory_limited_row_count = getattr(g, "bq_memory_limited_row_count", 0)
    g.bq_memory_limited = False; g.bq_memory_limited_row_count = 0
value = {..., "dttm": self.queried_dttm,  # Backwards compatibility
         "bq_memory_limited": self.bq_memory_limited, ...}
if self.is_loaded and key and self.status != QueryStatus.FAILED:
    self.set(key=key, value=value, timeout=timeout, ...)
```

**Flow:** `get`: no key / no backend / `force_query` → fresh manager (miss). Read exception → logged warning, `cache_value=None` → miss. Hit unpack sets `status=SUCCESS`, `is_loaded=True`, `is_cached=True`, restores bq flags; `KeyError` on malformed value is caught+logged (note ordering: `is_loaded=True` at :208 is set before later `cache_value["dttm"]` reads, so a partially-shaped hit can remain loaded with unset `cache_dttm`). `force_cached ∧ ¬loaded` → `CacheLoadError`. `set_query_result`: copies QueryResult fields, stamps `queried_dttm` as second-truncated UTC ISO, captures-and-resets `flask.g` BigQuery memory-limit flags only inside a request context, and writes **only** when `is_loaded ∧ key ∧ status≠FAILED`; any exception inside becomes `status=FAILED` with stacktrace instead of propagating.
**Invariant:** Cache-backend outages never fail a chart request; failed queries are never written to cache; `force_cached` is the one hard-failure mode (async/report paths rely on it).
**Probe:** `tests/unit_tests/common/test_query_cache_manager.py` — `test_get_cache_miss` (:24-36) pins miss shape (`is_loaded=False`, `cache_value=None`); `test_get_cache_backend_error_fails_open` (:38-57) injects `ConnectionError("connection refused")` as the backend read and asserts result parity with a fresh miss manager. Byte-exact source anchors verified this pass: comment "same as a cache miss and fall through to querying live data." at :185, write gate `if self.is_loaded and key and self.status != QueryStatus.FAILED:` at :150, `raise CacheLoadError("Error loading data from cache")` at :236.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "QueryCacheManager get set_query_result CacheLoadError", limit: 10 });
```

## Verdict
Adopt outage→miss degradation, never-cache-failures gating, and the single hard-raise on forced cache misses; adapt stats counters (`loading_from_cache` etc.) and BigQuery flag plumbing to your host; omit Flask `g` usage if you carry such flags differently. Coverage: whole class read at pin; dedicated unit file `test_query_cache_manager.py` (57 lines, two tests) read in full. File `no_recorded_issue`.
