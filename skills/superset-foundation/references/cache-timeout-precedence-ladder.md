<!-- capsule-v2 -->
# cache-timeout-precedence-ladder — Which of the five timeout sources wins for a chart-data query, and why can't `metrics` be used to detect filter-option queries?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** What is the exact precedence order for cache TTL resolution, and how are native-filter-option queries identified without false positives?

## QueryContextProcessor.get_cache_timeout + _is_native_filter_options_query
**Path/Symbol:** `superset/common/query_context_processor.py:560-600` (ladder) and `:602-635` (detector).
**Signature:** `def get_cache_timeout(self) -> int`; `@staticmethod def _is_native_filter_options_query(form_data: dict[str, Any]) -> bool`
**Data Shape:** config keys read: `NATIVE_FILTER_OPTIONS_CACHE_TIMEOUT`, `DATA_CACHE_CONFIG["CACHE_DEFAULT_TIMEOUT"]`, `CACHE_DEFAULT_TIMEOUT`; form_data fields `native_filter_id`, `viz_type`.

### Decisive source
```python
# Step 1: Request-level custom timeout (e.g., Force refresh bypass)
if self._query_context.custom_cache_timeout is not None:
    return self._query_context.custom_cache_timeout
# Step 2: Native filter option query override.
native_filter_timeout = current_app.config.get("NATIVE_FILTER_OPTIONS_CACHE_TIMEOUT")
if native_filter_timeout is not None and self._is_native_filter_options_query(
        self._query_context.form_data or {}):
    return native_filter_timeout
# Step 3: Slice, Dataset, or Database timeouts
if (cache_timeout := self._query_context.get_cache_timeout()) is not None:
    return cache_timeout
# Step 4: DATA_CACHE_CONFIG fallback.
if (data_cache_timeout := current_app.config["DATA_CACHE_CONFIG"].get(
        "CACHE_DEFAULT_TIMEOUT")) is not None:
    return data_cache_timeout
# Step 5: Global fallback.
return current_app.config["CACHE_DEFAULT_TIMEOUT"]
```

```python
return bool(form_data.get("native_filter_id")) and str(
    form_data.get("viz_type", "")
).startswith("filter_")
```

**Flow:** five-step first-match-wins ladder. The detector requires BOTH a `native_filter_id` field (set only by `nativeFilters/utils.ts::getFormData()`) AND a `viz_type` with the `filter_` prefix (`filter_select/range/time/timegrain/timecolumn`). The docstring records the trap explicitly: `form_data["metrics"]` must NOT be consulted — `getFormData()` unconditionally sets `metrics: ["count"]` for every native-filter request regardless of `sortMetric`, so a `not form_data.get("metrics")` condition would always be False in production and silently disable the override. A returned timeout equal to `CACHE_DISABLED_TIMEOUT` also flips `force_query` in the acquisition ladder (see `df-payload-acquisition-ladder`), making this ladder not just TTL selection but freshness policy.
**Invariant:** Precedence is total and short-circuits; per-request custom timeout beats everything; operator-configured filter-options TTL beats slice/datasource defaults; two global fallbacks close the ladder with no `None` ever escaping.
**Probe:** `tests/integration_tests/charts/data/api_tests.py:1766-1773` (`test_native_filter_uses_native_filter_options_cache_timeout` — config `native_filter_timeout=9999, data_cache_timeout=3456` ⇒ response `cache_timeout == 9999`) and `:1780-1795` (`test_native_filter_overrides_dataset_timeout` — datasource `cache_timeout=86400` still loses to the filter-options override at 300). Byte-exact detector anchor verified this pass at `query_context_processor.py:635` (`startswith("filter_")`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "get_cache_timeout native filter options timeout precedence", limit: 10 });
```

## Verdict
Adopt the ordered ladder shape and the two-signal conjunctive detection rule; adapt config key names and the slice/datasource chain to your model; omit the metrics-trap warning only if your producer cannot inject misleading defaults. Coverage: both ranges read directly at pin; two integration tests read directly (:1766-1795). File `no_recorded_issue`.
