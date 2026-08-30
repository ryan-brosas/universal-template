<!-- capsule-v2 -->
# Async logging handler twins — how acompletion drives success/failure logging without blocking the request

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** Where do the async success/failure handler bodies live, how do they stay in parity with the sync bodies, and what decides whether a request's logging runs on the async worker, the thread executor, or both?

## _async_success_handler_body / _async_failure_handler_body
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging._async_success_handler_body` (:2697-2998), `Logging._async_failure_handler_body` (:3311-3375); wrappers `async_success_handler` (:2680-2695) and `async_failure_handler` (:3292-3309, restores trace_id/session_id contextvars in `finally`).
**Signature:** `async _async_success_handler_body(self, result=None, start_time=None, end_time=None, cache_hit=None, **kwargs) -> None`; `async _async_failure_handler_body(self, exception, traceback_exception, start_time=None, end_time=None) -> None`.
**Data Shape:** same `model_call_details` dict as the sync bodies; async bodies additionally stamp `async_complete_streaming_response` and read the `dynamic_async_{success,failure}_callbacks` lists against globals `litellm._async_success_callback` / `litellm._async_failure_callback`.

### Decisive source
```python
# litellm_logging.py:2709-2712 (abridged) — the guard differs from the sync body
if not self._is_assembled_stream_success(result) and not self.should_run_logging(
    event_type="async_success"
):  # prevent double logging (non-streaming)
    return
...
# litellm_logging.py:2760-2766 — parity point: the SAME helper as the sync body
start_time, end_time, result = self._success_handler_helper_fn(
    start_time=start_time, end_time=end_time, result=result, cache_hit=cache_hit,
    standard_logging_object=kwargs.get("standard_logging_object", None),
)
```

**Flow:** async success body: (1) guard — per-chunk calls are double-log-latched by `should_run_logging("async_success")`, but a final ASSEMBLED stream export bypasses the latch (`_is_assembled_stream_success` is true) and is deduped instead by the dispatch-plane stamp; (2) batch-cost block for `aretrieve_batch` + `LiteLLMBatch` results (`batch_ignore_default_logging` short-circuit, base64 unified-file-id check, explicit `batch_cost/batch_usage/batch_models` kwargs vs `await _handle_completed_batch`); (3) shared `_success_handler_helper_fn` (see sibling capsule); (4) assemble complete streaming response with re-entry short-circuit on the `async_complete_streaming_response` key, compute cost (cache_hit→0.0, NotFoundError→None), build+emit standard payload; pass-through branch preserves pre-computed cost; (5) combined callback list from `dynamic_async_success_callbacks` + `litellm._async_success_callback`; (6) redact → per-callback `async_logging_hook` pass (CustomGuardrail `logging_only` gate; CustomLogger gets `redact_message_input_output_from_custom_logger` first) → `has_run_logging("async_success")` stamp → per-callback loop with `should_run_callback` gate, openmeter/dynamodb special cases, CustomLogger stream-vs-non-stream dispatch (`async_log_stream_event` vs `async_log_success_event`); every per-callback exception swallowed + `_handle_callback_failure` Prometheus counter. Async failure body: `special_failure_handlers` FIRST (model-group rate-limit event → `log_model_group_rate_limit_error` on `_async_failure_callback` CustomLoggers), then the same shape minus redaction and hook passes (result is None).
**Invariant:** Parity with the sync bodies comes from the shared helper functions, NOT from duplicated logic — any new normalization must land in `_success/_failure_handler_helper_fn` or one twin silently diverges. The assembled-stream bypass of the double-log latch is safe only because `dispatch_success_handlers` stamps `has_dispatched_final_stream_success` exactly once.
**Probe:** `tests/test_litellm/litellm_core_utils/test_litellm_logging.py` -k "dispatch_success_handlers or dispatch_failure_handlers or prevent_double_logging" executed live at the pin → 8 passed (incl. `test_dispatch_success_handlers_invokes_callbacks_once_for_final_stream` :1223, which pins that a second final-stream dispatch does not re-export).

## Drive sites — where acompletion actually fires the handlers
**Path/Symbol:** `litellm/utils.py` — `wrapper_async` success path (:1821-1848) via `_client_async_logging_helper` (:1137-1166); failure path (:1872-1885). Worker: `litellm/litellm_core_utils/logging_worker.py` — `LoggingWorker.ensure_initialized_and_enqueue` (:333), bounded best-effort queue with atexit flush.
**Signature:** `async _client_async_logging_helper(logging_obj, result, start_time, end_time, is_completion_with_fallbacks) -> None`.

### Decisive source
```python
# utils.py:1144-1166 (abridged)
if is_completion_with_fallbacks is False:  # don't log the parent event ... double logging ... issue #7477
    GLOBAL_LOGGING_WORKER.ensure_initialized_and_enqueue(
        async_coroutine=logging_obj.async_success_handler(result=result, start_time=start_time, end_time=end_time)
    )
    logging_obj.handle_sync_success_callbacks_for_async_calls(result=result, start_time=start_time, end_time=end_time)
...
# utils.py:1877-1883 (failure path)
logging_obj.failure_handler(e, traceback_exception, start_time, end_time)  # DO NOT MAKE THREADED - router retry fallback relies on this!
...
await logging_obj.async_failure_handler(e, traceback_exception, start_time, end_time)
```

**Flow:** success — `asyncio.create_task(_client_async_logging_helper)` (or deferred via `logging_obj._enqueue_deferred_logging` when set): the async handler coroutine goes onto the background LoggingWorker queue (never awaited inline — callbacks must not add latency to the response), while sync-only integrations (langfuse/s3) are submitted through `executor.submit(success_handler)` but ONLY when `_should_run_sync_callbacks_for_async_calls` finds non-internal sync callbacks (internal `_PROXY_`/service-logger callbacks filtered out). Failure — the sync `failure_handler` runs INLINE and synchronously (router retry/fallback logic reads its side effects before continuing), then `async_failure_handler` is awaited. The `completion_with_fallbacks` parent event never logs success (its children already did).
**Invariant:** Success logging is fire-and-forget (bounded queue, best-effort, atexit flush); failure logging has a synchronous component that retry logic depends on. Reversing either direction breaks either latency or retry correctness.
**Probe:** same live suite as above (8 passed); `handle_sync_success_callbacks_for_async_calls` gating read at :3429-3481 (filter chain: combined list → remove internal CustomLogger-compatible → remove internal `_PROXY_`/service-logger names → non-empty check).

## dispatch_success_handlers / dispatch_failure_handlers — the routing plane
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging.dispatch_success_handlers` (:1766-1819), `Logging.dispatch_failure_handlers` (:1821-1848), `Logging._is_sync_litellm_request` (:1734-1746), `Logging._is_assembled_stream_success` (:1748-1764). Callers: responses/interactions/a2a streaming iterators + proxy common_request_processing/pass-through handlers.
**Signature:** `async dispatch_success_handlers(self, result=None, start_time=None, end_time=None, cache_hit=None, prefer_async_handlers=False, **kwargs) -> None`.
**Data Shape:** `_is_sync_litellm_request` = no `a*` call-type flag (`acompletion`, `aresponses`, `aembedding`, `aimage_generation`, `atranscription`, `allm_passthrough_route`, `aanthropic_messages`, `agenerate_content[_stream]`) set in `litellm_params`.

### Decisive source
```python
# litellm_logging.py:1783-1807 (abridged)
if self._is_assembled_stream_success(result):
    if self.model_call_details.get("has_dispatched_final_stream_success"):
        return
    self.model_call_details["has_dispatched_final_stream_success"] = True
...
if sync_sdk and not prefer_async_handlers and not passthrough:
    self.success_handler(result, start_time=start_time, end_time=end_time, cache_hit=cache_hit, **kwargs)
    return
await self.async_success_handler(result, start_time=start_time, end_time=end_time, cache_hit=cache_hit, **kwargs)
if not self._should_run_sync_callbacks_for_async_calls():
    return
executor.submit(self.success_handler, result, start_time=start_time, end_time=end_time, cache_hit=cache_hit, **kwargs)
```

**Flow:** (1) final-assembled-stream dedup stamp (once only); (2) sync-SDK shortcut — a purely sync request with no preference flag and no passthrough goes straight to the sync handler and returns; (3) otherwise await the async handler, then submit the sync handler on the executor only if non-internal sync callbacks exist. `dispatch_failure_handlers` mirrors this with the failure lists.
**Invariant:** The sync and async handlers never run concurrently on the shared logging object (docstring contract of `dispatch_failure_handlers`); treating a per-chunk `ModelResponseStream` as the assembled result would prematurely set the dedup stamp and suppress the real final log — hence `_is_assembled_stream_success` requires a non-stream result OR an existing `complete_streaming_response` key.
**Probe:** `test_dispatch_success_handlers_sync_path_invokes_callback_once_for_final_stream` (:1285), `test_dispatch_prefer_async_handlers_runs_legacy_callbacks` (:1342), `test_dispatch_success_handlers_invokes_async_callback_for_pass_through` (:1388), `test_dispatch_failure_handlers_prefer_async_does_not_submit_sync_handler` (:1423) — all in the live 8-passed suite above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "_async_success_handler_body _async_failure_handler_body dispatch_success_handlers",
  filePattern: "litellm_logging.py", limit: 20 });
// → rank-1..n surface both twin bodies (:2697/:3311), the dispatch plane (:1766/:1821), and the guard helpers (:1734/:1748)
```

## Verdict
Adopt the shared-helper parity pattern, the assembled-stream latch bypass + dispatch-stamp dedup pair, the fire-and-forget success queue vs inline-sync-failure split, and the internal-callback filter before submitting sync work for async calls. Adapt the named-integration special cases (openmeter/dynamodb branches) to your sink registry, and the LoggingWorker bounds (queue size, per-coroutine timeout, aggressive-clear cooldown — see next-pass targets) to your latency budget. Omit the batch-cost block unless you port batch polling. Coverage caveat: LoggingWorker internals beyond the enqueue contract were not deep-read this pass (recorded as next-pass target 2).
