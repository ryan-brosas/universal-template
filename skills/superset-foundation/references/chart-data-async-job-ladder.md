<!-- capsule-v2 -->
# chart-data-async-job-ladder — How do you gate sync vs async chart-data execution and hand off to a background job without breaking cache-key consistency?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A chart-data request may run synchronously or as a background job — what decides which, what does the handoff carry, and how does the worker later produce the same cache key the sync path would have?

## Async gate + job submission ladder
**Path/Symbol:** `superset/charts/data/api.py` — `use_async` gates (:237-248 in `get_data`, :341-352 in `data`), `_run_async` (:435-468); `superset/commands/chart/data/create_async_job_command.py` — `CreateAsyncChartDataJobCommand.validate/run` (whole file); `superset/async_events/async_query_manager.py` — `AsyncQueryManager.submit_chart_data_job` (:309-335).
**Signature:** `_run_async(self, form_data: dict[str, Any], command: ChartDataCommand, add_extra_log_payload=None) -> Response`; `submit_chart_data_job(self, channel_id: str, form_data: dict[str, Any], user_id: Optional[int] = None) -> dict[str, Any]`.
**Data Shape:** gate inputs: feature flag `GLOBAL_ASYNC_QUERIES`, `result_format == JSON`, `result_type == FULL`, `cache_timeout != CACHE_DISABLED_TIMEOUT`. Job metadata out: `{channel_id, job_id, user_id, status, errors, result_url}` returned as HTTP 202 body.

### Decisive source
```python
# Don't use async queries when cache is disabled (cache_timeout=-1)
# as async queries depend on caching to retrieve results
cache_timeout = query_context.get_cache_timeout()
use_async = (
    is_feature_enabled("GLOBAL_ASYNC_QUERIES")
    and query_context.result_format == ChartDataResultFormat.JSON
    and query_context.result_type == ChartDataResultType.FULL
    and cache_timeout != CACHE_DISABLED_TIMEOUT
)
if use_async:
    return self._run_async(json_body, command, add_extra_log_payload)
```
```python
def _run_async(self, form_data, command, add_extra_log_payload=None):
    # First, look for the chart query results in the cache,
    # but only if we're not forcing a refresh.
    if not form_data.get("force"):
        try:
            result = command.execute(force_cached=True)
            if result is not None:
                self._log_is_cached(result.materialize(), add_extra_log_payload)
                return self._send_chart_response(result)
        except ChartDataCacheLoadError:
            pass
    # Otherwise, kick off a background job to run the chart query.
    # Clients will either poll or be notified of query completion,
    # at which point they will call the /data/<cache_key> endpoint
    # to retrieve the results.
    async_command = CreateAsyncChartDataJobCommand()
    try:
        async_command.validate(request)
    except AsyncQueryTokenException:
        return self.response_401()
    async_result = async_command.run(form_data, get_user_id())
    return self.response(202, **async_result)
```
```python
# if it's guest user, we want to pass the guest token to the celery task
# chart data cache key is calculated based on the current user
# this way we can keep the cache key consistent between sync and async command
# so that it can be looked up consistently
job_metadata = self.init_job(channel_id, user_id)
self._load_chart_data_into_cache_job.apply_async(
    args=[
        {**job_metadata, "guest_token": guest_user.guest_token}
        if (guest_user := security_manager.get_current_guest_user_if_guest())
        else job_metadata,
        form_data,
    ],
    # Use job_id as the Celery task id so the cancel endpoint can revoke
    # the running task by the id the client already holds.
    task_id=job_metadata["job_id"],
    expires=self._jwt_expiration_seconds,
)
```

**Flow:** validate context first (`ChartDataCommand.validate()` ⇒ `raise_for_access`) → compute the four-conjunct async gate → if async: unless `force`, try `execute(force_cached=True)` — hit returns synchronously with `is_cached` logged; `ChartDataCacheLoadError` falls through → two-phase job creation: `validate(request)` parses the channel id (bad token ⇒ 401 BEFORE any submission), then `run(form_data, user_id)` submits the celery task carrying guest-token-inflated job metadata when the caller is a guest → 202 with job metadata; the timing sidecar is never projected onto the 202 body.
**Invariant:** The async path must be unreachable when caching is disabled (results are retrieved via the cache); the worker must compute the identical user-bound cache key as the sync path (hence guest-token propagation); `task_id == job_id` so cancellation targets the client-held id; channel-id validation must precede submission (no orphan jobs for unauthenticated channels).
**Probe:** `tests/integration_tests/charts/data/api_tests.py:763-778` pins 202 + exact six-key body; :780-829 pins cached-hit synchronous 200 with `execute(force_cached=True)` and `is_cached=True` logged; :865-910 pins `force=true` skipping the cache check entirely (`mock_execute.assert_not_called()`); :912-922 pins non-FULL result_type staying synchronous; :924-936 pins invalid channel token ⇒ 401. Unit: `tests/unit_tests/charts/test_chart_data_api.py:585-619` pins no `timing` in the 202 body even with `CHART_DATA_INCLUDE_TIMING=True`; :621-647 pins opt-in timing on the cached synchronous result.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "chart data async job submit force_cached GLOBAL_ASYNC_QUERIES guest token", limit: 10 });
```

## Verdict
Adopt the four-conjunct gate (feature flag ∧ format ∧ type ∧ cache-enabled), the try-cache-first-then-submit ladder, validate-before-run two-phase job creation, and identity-carrying submission (user/guest token for key consistency, job id as task id); adapt the queue transport (Celery `apply_async`/`expires`) to your host's job system; omit Superset's event-stream channel protocol beyond the 202 metadata shape. Coverage: api.py read whole (1868L); both direct test files read at the cited ranges; MCP disconnected this pass — Retrieve is a documented target, probes below are the executed evidence.
