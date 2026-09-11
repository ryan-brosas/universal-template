<!-- capsule-v2 -->
# Logging callback fan-out — how one success/failure event reaches every integration exactly once

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** When a call succeeds or fails, in what order and under which guards does `Logging` deliver the event to named integrations, CustomLogger classes, and custom functions — and what stops double delivery?

## success_handler / failure_handler bodies
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging.success_handler` (:2246-2261) → `_success_handler_body` (:2263-2678); `async_success_handler` (:2680-2695) → `_async_success_handler_body`; `Logging.failure_handler` (:3098-3115) → `_failure_handler_body` (:3117-3290); guards `should_run_logging` (:1850-1861) / `has_run_logging` (:1863-1873).
**Signature:** `success_handler(self, result=None, start_time=None, end_time=None, cache_hit=None, **kwargs) -> None`; `failure_handler(self, exception: Exception, traceback_exception: str, start_time=None, end_time=None) -> None`.
**Data Shape:** state lives in `self.model_call_details`; callback list = `get_combined_callback_list(dynamic_…_callbacks, litellm.success_callback|failure_callback)` — entries are strings ("langfuse", "s3", …), `CustomLogger` instances, or plain callables.

### Decisive source
```python
# litellm_logging.py:2264-2265 + 2318-2337 (abridged) — guard, then transform-before-fanout
if not self.should_run_logging(event_type="sync_success"):  # prevent double logging
    return
...
callbacks: Final = self.get_combined_callback_list(
    dynamic_success_callbacks=self.dynamic_success_callbacks,
    global_callbacks=litellm.success_callback,
)
## REDACT MESSAGES ##
result = redact_message_input_output_from_logging(
    model_call_details=(self.model_call_details if hasattr(self, "model_call_details") else {}),
    result=result,
)
## LOGGING HOOK ##  # CustomGuardrail (logging_only gate) / CustomLogger.logging_hook may rewrite kwargs+result
...
self.has_run_logging(event_type="sync_success")
for callback in callbacks:
    try:
        should_run = self.should_run_callback(callback=callback, litellm_params=litellm_params,
                                              event_hook="success_handler")
        if not should_run:
            continue
        ...
        if isinstance(callback, CustomLogger) and is_sync_request \
                and self.call_type != CallTypes.pass_through.value:
            ... callback.log_success_event(kwargs=self.model_call_details, response_obj=result, ...)
        if callable(callback) is True and is_sync_request and customLogger is not None:
            customLogger.log_event(..., callback_func=callback)
    except Exception as e:
        print_verbose(f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while success logging ...")
        if capture_exception:
            capture_exception(e)
```

**Flow:** per body: (1) event-typed double-log guard returns early if `has_logged_<event_type>` is already stamped; (2) streaming responses are assembled once (`complete_streaming_response`) with `response_cost` computed from the assembled object; (3) combined callback list resolved; (4) result redacted *before* any hook or sink sees it; (5) `logging_hook` pass lets guardrails/loggers rewrite `model_call_details` + result; (6) `has_run_logging` stamps the flag; (7) per-callback loop with `should_run_callback` filter; sync requests dispatch `CustomLogger.log_success_event`, async ones are served by the async handler twin (pass-through calls excluded from sync dispatch); (8) every per-callback exception is swallowed (printed + sentry + `_handle_callback_failure` Prometheus counter) so one broken integration never fails the request.
**Invariant:** Exactly-once per event type — the four flags `has_logged_{sync,async}_{success,failure}` are independent (`test_logging_prevent_double_logging`: after `has_run_logging("sync_success")`, only `sync_success` reports False). Fan-out is fail-soft: no callback error propagates. The whole body sits in an outer try that only logs. Handlers restore trace_id/session_id contextvars in `finally` even when callbacks nest further litellm calls.
**Probe:** `tests/test_litellm/litellm_core_utils/test_litellm_logging.py::test_logging_prevent_double_logging` (:835-845) executed live at the pin → 1 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "Logging success_event failure_event handle_success handle_failure",
  filePattern: "litellm_logging.py", limit: 40 });
// → rank-1..n surface should_run_logging/has_run_logging/success_handler/failure_handler with exact lines
```

## Verdict
Adopt the event-typed once-only latch, redact-before-hooks ordering, per-sink exception isolation, and the sync/async handler split keyed off `litellm_params`-derived `is_sync_request`. Adapt the named-integration if-chain to your sink registry (litellm hardcodes each vendor branch). Omit the vendor-specific payload massaging (supabase/langfuse/s3 stream gating) unless you port those sinks verbatim. The `_async_*_handler_body` interiors, `should_run_callback`, and the `*_helper_fn` payload helpers were deep-read in pass 5 — see sibling capsules `async-logging-handler-twins` and `logging-callback-gate-and-payload-helpers`.
