<!-- capsule-v2 -->
# cache-replay-opaque-key-skip — How do you serve pre-computed results from an opaque cache key without re-running the SQL-injection check?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** The async flow's result endpoint takes only a cache key from the client — what makes that safe, and why must the novel-SQL filter check be skipped for replays instead of re-run?

## Cache-replay endpoint + replay flag
**Path/Symbol:** `superset/charts/data/api.py` — `data_from_cache` (:375-433); `superset/charts/data/query_context_cache_loader.py` — `QueryContextCacheLoader.load` (whole file); `superset/security/manager.py` — `_sql_filters_modified` (:1383-1410).
**Signature:** `data_from_cache(self, cache_key: str) -> Response`; `load(cache_key: str) -> dict[str, Any]`; `_sql_filters_modified(query_context, form_data, stored_chart, stored_query_context) -> bool`.
**Data Shape:** cache value = `{"data": <query-context form dict>}` under a `qc-`-prefixed SHA-256 key; replay flag `_from_cache_replay: bool` set on the reconstructed QueryContext; error map 404/403/400 at load, 422 sanitized downstream.

### Decisive source
```python
cached_data = self._load_query_context_form_from_cache(cache_key)
# Set form_data in Flask Global as it is used as a fallback
# for async queries with jinja context
set_form_data(cached_data)
query_context = self._create_query_context_from_form(cached_data)
# Mark as a cache replay so _sql_filters_modified skips the
# SQL-extras check.  The original request already passed the
# full security check, cache keys are opaque SHA-256 hashes
# (unguessable), and force_cached only serves pre-computed
# data — no new SQL is executed.
query_context._from_cache_replay = True
command = ChartDataCommand(query_context)
command.validate()
```
```python
# Cache-replay requests (``/data/<cache_key>``) are skipped: the original
# request already passed the full check, and ``_sanitize_filters`` may have
# rewritten ``extras`` in place before caching (comment normalization,
# Jinja rendering), making byte-equality comparison unreliable.
if getattr(query_context, "_from_cache_replay", False) is True:
    return False
```

**Flow:** load form dict by opaque key (miss ⇒ `ChartDataCacheLoadError` ⇒ 404) → restore form data into the request-global jinja fallback → reconstruct QueryContext → set the replay flag → run the normal `command.validate()` (access check still runs under the current user) → execute with `force_cached=True` so only pre-computed data is served; the security layer's novel-SQL detector returns False immediately for flagged replays.
**Invariant:** Three independent properties must all hold to justify the skip: keys are unguessable (SHA-256, not derived from user input), execution is `force_cached` (no new SQL runs), and the original request already passed the full check. Re-running byte-equality on cached extras is unsound because sanitization rewrites them in place before caching — the skip is correctness, not laziness. Access validation (`raise_for_access`) is NOT skipped: a different user hitting a leaked key still gets 403.
**Probe:** `tests/integration_tests/charts/data/api_tests.py:1439-1464` pins replay 200 with `force_cached=True` asserted inside the mocked execute; :1466-1482 pins downstream failure ⇒ 422 "Error loading data from cache"; :1484-1510 pins unauthenticated replay ⇒ 401; :1512-1523 pins unknown key ⇒ 404.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "data_from_cache _from_cache_replay sql filters modified skip", limit: 10 });
```

## Verdict
Adopt the opaque-key replay pattern with its three-property justification and the early-return skip in the novel-SQL detector; keep access validation running on replays; adapt the flag mechanism to your context object (a plain attribute read via `getattr(..., False)` keeps old contexts safe); omit Superset's Flask `set_form_data` global plumbing. Coverage: api.py read whole; loader file read whole (30L); manager.py read at :1383-1440; integration tests read at cited ranges; MCP disconnected this pass — Retrieve is a documented target.
