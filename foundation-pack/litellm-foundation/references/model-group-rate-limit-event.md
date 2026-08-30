<!-- capsule-v2 -->
# Model-group rate-limit event — special_failure_handlers and the no_deployments_available cross-check

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** How does a router "no deployments available" failure become a distinct callback event (`log_model_group_rate_limit_error`), what exactly gates it, and where do the matching raise sites live?

## The gate — exception-string match OR single-deployment base case
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging.special_failure_handlers` (:3066-3097); call site `_async_failure_handler_body` (:3321); event default `litellm/integrations/custom_logger.py` — `CustomLogger.log_model_group_rate_limit_error` (:308-311); error vocabulary `litellm/types/router.py` — `RouterErrors.no_deployments_available` (:574), `RouterRateLimitErrorBasic` (:773-784), `RouterRateLimitError` (:787-800).
**Signature:** `async special_failure_handlers(self, exception: Exception) -> None`; `async log_model_group_rate_limit_error(self, exception: Exception, original_model_group: str | None, kwargs: dict) -> None` (default body: `pass`).

### Decisive source
```python
# litellm_logging.py:3077-3096 (abridged)
## BASE CASE ## check if rate limit error for model group size 1
is_base_case = False
if metadata.get("model_group_size") is not None:
    if isinstance(model_group_size, int) and model_group_size == 1:
        is_base_case = True
## check if special error ##
if RouterErrors.no_deployments_available.value not in str(exception) and is_base_case is False:
    return
model_group: Final = metadata.get("model_group") or None
for callback in litellm._async_failure_callback:
    if isinstance(callback, CustomLogger):
        await callback.log_model_group_rate_limit_error(
            exception=exception, original_model_group=model_group, kwargs=self.model_call_details)
```

**Flow:** the async failure body calls `special_failure_handlers` FIRST — before the double-log latch `should_run_logging("async_failure")` — so the event fires on EVERY async failure attempt, not just the first logged one. The gate has two independent triggers: (1) the exception string contains the exact `RouterErrors.no_deployments_available` value ("No deployments available for selected model"); (2) BASE CASE — `metadata["model_group_size"] == 1`, because a single-deployment group has no failover, so ANY failure of that attempt is effectively a group-level rate-limit signal. When triggered, every CustomLogger in `litellm._async_failure_callback` gets the awaited event with the original model group from metadata; non-CustomLogger callbacks are skipped, and the default implementation is a no-op so plain integrations pay nothing.
**Invariant:** Firing BEFORE the double-log latch is deliberate — per-attempt visibility for alerting, while the rest of the failure fan-out stays once-only. The string match couples this event to the router's exact error vocabulary: rewording `RouterRateLimitError`'s message silently kills the event.
**Probe:** direct test BLOCKED at the pin — `tests/logging_callback_tests/test_custom_callback_router.py::test_rate_limit_error_callback` (mock_response RateLimitError router + AsyncMock on `log_model_group_rate_limit_error`, asserts called-once with `original_model_group == "my-test-gpt"`) fails collection with `ModuleNotFoundError: vcr` at `tests/_vcr_conftest_common.py:21` (observed live this pass). Evidence chain = full source read below instead.

## Raise-site cross-check — where the matched string comes from
**Path/Symbol:** `litellm/router.py` — `RouterRateLimitError` raises at :12035 (get_available_deployment, zero healthy after filters), :12068 (strategy returned None), :12178/:12212 (pass-through twin sites); `RouterRateLimitErrorBasic` at :10868 (pre-call-checks: all deployments invalid AND the cause was a rate-limit error, else ContextWindowExceededError); metadata stamping at :6667-6672.

### Decisive source
```python
# types/router.py:799 — the message embeds the matched constant
_message = f"{RouterErrors.no_deployments_available.value}, Try again in {cooldown_time} seconds. Passed model={model}. pre-call-checks={enable_pre_call_checks}, cooldown_list={cooldown_list}"
...
# router.py:6667-6672 — model_group_size stamped only when a str model_group exists
if "model_group" in _metadata and isinstance(_metadata["model_group"], str):
    model_list: Final = self.get_model_list(model_name=_metadata["model_group"])
    if model_list is not None:
        _metadata.update({"model_group_size": len(model_list)})
```

**Flow:** all four `RouterRateLimitError` sites compute the same payload triple before raising — `cooldown_cache.get_min_cooldown(model_ids)` for the retry hint, `_get_cooldown_deployments(...)` for the list, and `self.enable_pre_call_checks` — so the message always carries actionable recovery data. The base-case input (`model_group_size`) is stamped by the router's retry wrapper into request metadata only when the caller's metadata already names a string `model_group`; without that stamp the base case can never fire.
**Invariant:** The event's two triggers map 1:1 to router behavior: multi-deployment exhaustion → the string-matched error; single-deployment groups → the size-stamped base case. Both inputs are produced exclusively by the router, so SDK-direct calls never emit this event.
**Probe:** source-read at the pin (all five raise sites + both error classes + the stamping block); the blocked upstream test above pins the end-to-end shape when the vcr runner is available.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "special_failure_handlers log_model_group_rate_limit_error",
  filePattern: "litellm_logging.py", limit: 10 });
// → rank-1 Logging.special_failure_handlers :3066-3097
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "RouterRateLimitError no_deployments_available cooldown_time",
  filePattern: "router.py", limit: 20 });
// → the four raise sites (:12035/:12068/:12178/:12212) plus the basic variant (:10868)
```

## Verdict
Adopt the two-trigger gate (exact error-vocabulary string match OR single-deployment base case), the fire-before-double-log-latch ordering for per-attempt alerting events, the awaited CustomLogger-only dispatch with a no-op default, and the recovery-data payload (min cooldown + cooldown list + pre-call-checks flag) computed at every raise site. Keep the metadata stamping conditional on an existing string model_group so non-router callers stay silent. Adapt the error-vocabulary constant to your router's own message grammar — the string coupling is the fragility to manage. Omit nothing structural. Coverage caveat: the end-to-end test is vcr-blocked at the pin; the evidence chain is the full source read recorded here.
