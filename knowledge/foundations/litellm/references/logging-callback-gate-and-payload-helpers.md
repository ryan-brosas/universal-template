<!-- capsule-v2 -->
# Logging callback gate + payload helpers — which callbacks actually run, and how cost/times normalize before the standard payload

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** When a success or failure event fires, which per-callback gate decides whether each integration runs, and how are start/end times, response cost, and the standard logging payload normalized before any callback sees them?

## should_run_callback three-rung gate
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging.should_run_callback` (:1875-1897); consulted inside both sync and async fan-out loops before every callback dispatch.
**Signature:** `should_run_callback(self, callback: litellm.CALLBACK_TYPES, litellm_params: dict, event_hook: str) -> bool`.
**Data Shape:** `callback` is a string ("langfuse"), a `CustomLogger` instance, or a plain callable; `litellm_params` carries the per-request `"no-log"` flag; `event_hook` is only used for debug logging.

### Decisive source
```python
# litellm_logging.py:1875-1897 (abridged)
def should_run_callback(self, callback, litellm_params, event_hook) -> bool:
    if litellm.global_disable_no_log_param:
        return True
    if litellm_params.get("no-log", False) is True:
        # proxy cost tracking cal backs should run
        if not (isinstance(callback, CustomLogger) and "_PROXY_" in callback.__class__.__name__):
            verbose_logger.debug("no-log request, skipping logging for %s event", event_hook)
            return False
    if EnterpriseCallbackControls is not None and EnterpriseCallbackControls.is_callback_disabled_dynamically(
        callback=callback, litellm_params=litellm_params,
        standard_callback_dynamic_params=self.standard_callback_dynamic_params,
    ):
        return False
    return True
```

**Flow:** rung 1 — `litellm.global_disable_no_log_param` (operator kill-switch) forces every callback to run regardless of no-log; rung 2 — a request-level `no-log: True` skips everything EXCEPT `CustomLogger` instances whose class name contains `_PROXY_` (proxy cost tracking must survive no-log requests); rung 3 — enterprise dynamic disable via the `x-litellm-disable-callbacks` header can veto individual callbacks; otherwise run.
**Invariant:** The gate is consulted PER CALLBACK inside the fan-out loop (not once per event), so one integration can be header-disabled while others still fire; the `_PROXY_` class-name carve-out is the only no-log exemption and it is name-based, not capability-based.
**Probe:** `tests/local_testing/test_custom_callback_input.py::test_litellm_logging_no_log_param` (:1577-1602, pins both kill-switch directions of rung 1/2) — BLOCKED this pass by missing `vcr` at conftest import (re-observed); behavior confirmed by source read. Adjacent runnable evidence: the four helper-fn tests below passed live.

## _success_handler_helper_fn — shared by both twins
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging._success_handler_helper_fn` (:2047-2122); call sites: sync `_success_handler_body` :2274, async `_async_success_handler_body` :2760.
**Signature:** `_success_handler_helper_fn(self, result=None, start_time=None, end_time=None, cache_hit=None, standard_logging_object=None) -> tuple[start_time, end_time, result]`.
**Data Shape:** mutates `self.model_call_details` (stamps `log_event_type="successful_api_call"`, `end_time`, `cache_hit`, `completion_start_time`, `litellm_params.metadata.hidden_params`, `response_cost`, `standard_logging_object`); returns normalized times + possibly transformed result.

### Decisive source
```python
# litellm_logging.py:2080-2099 (abridged) — the three-way branch
if standard_logging_object is None and result is not None and self.stream is not True:
    if self._is_recognized_call_type_for_logging(logging_result=logging_result) or isinstance(logging_result, (dict, list)):
        self._process_hidden_params_and_response_cost(logging_result=logging_result, start_time=start_time, end_time=end_time)
elif standard_logging_object is not None:
    self.model_call_details["standard_logging_object"] = standard_logging_object
else:
    # Streaming reaches here before its cost is known ... A pass-through stream cannot
    # (its body is opaque) and carries the cost its upstream reported in the response
    # headers, which an unconditional reset would discard.
    self.model_call_details.setdefault("response_cost", None)
```

**Flow:** (1) normalize times — `start_time` defaults to `self.start_time`, `end_time` to now, `completion_start_time` defaults to `end_time`; (2) per-call-type result conversion (anthropic_messages / generate_content / a2a send_message handlers); (3) `normalize_logging_result` (realtime list → combined usage object; passthrough `Response` → provider config's `logging_non_streaming_response`); (4) the three-way branch above — recognized non-stream results go through cost+payload processing, pre-built payloads are stored as-is, streaming-before-cost seeds `response_cost` with `setdefault` so an existing value (e.g. upstream-reported passthrough cost) is NEVER reset; (5) `_transform_usage_objects` rewrites ResponsesAPI/Transcription usage into chat format via `model_copy()` (original object untouched); (6) global `max_budget` accumulation for non-stream dict results. Any exception is wrapped as `[Non-Blocking] LiteLLM.Success_Call Error`.
**Invariant:** Exactly one standard payload per non-streaming success — `test_non_streaming_computes_standard_logging_object_once` pins `get_standard_logging_object_payload` call_count == 1 through a real `acompletion`. The streaming branch must stay `setdefault`, never assignment.
**Probe:** `tests/test_litellm/litellm_core_utils/test_litellm_logging.py::test_non_streaming_computes_standard_logging_object_once` (:3060) + `test_emit_standard_logging_payload_called_for_non_streaming` (:3084) executed live at the pin → 2 passed.

## _process_hidden_params_and_response_cost — the cost ladder
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging._process_hidden_params_and_response_cost` (:1964-2001) → `_build_standard_logging_payload` (:2003-2018, accumulates construction time into `callback_duration_ms`).
**Signature:** `_process_hidden_params_and_response_cost(self, logging_result, start_time, end_time) -> None`.

### Decisive source
```python
# litellm_logging.py:1981-1991
if self.model_call_details.get("cache_hit") is True:
    self.model_call_details["response_cost"] = 0.0
elif "response_cost" in hidden_params:
    self.model_call_details["response_cost"] = hidden_params["response_cost"]
elif (existing_cost := self.model_call_details.get("response_cost")) is not None and existing_cost != 0:
    # Preserve response_cost if already calculated (e.g., by pass-through
    # handlers like Gemini/Vertex which call completion_cost directly).
    # Do not preserve 0 from failure_handler on intermediate router retries.
    pass
else:
    self.model_call_details["response_cost"] = self._response_cost_calculator(result=logging_result)
```

**Flow:** hidden params copied into `litellm_params.metadata.hidden_params` → cost ladder (cache_hit→0.0 > provider-reported hidden cost > pre-existing NON-ZERO cost preserved > compute) → build standard payload → `emit_standard_logging_payload`.
**Invariant:** A zero cost from an intermediate failed router retry must NOT be preserved (the `!= 0` guard), while a positive pre-computed cost (pass-through handlers) must survive. This asymmetry is the whole point of rung 3.
**Probe:** `tests/test_litellm/litellm_core_utils/test_litellm_logging.py::test_async_success_handler_preserves_response_cost_for_pass_through_endpoints` (:3108, regression for the PR #19887 unconditional-reset bug) + `test_response_cost_calculator_with_response_cost_in_hidden_params` (:1982) executed live at the pin → 2 passed.

## _failure_handler_helper_fn — early-failure tolerance
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging._failure_handler_helper_fn` (:3022-3064); called by sync `_failure_handler_body` and async `_async_failure_handler_body` (:3324).
**Signature:** `_failure_handler_helper_fn(self, exception, traceback_exception, start_time=None, end_time=None) -> tuple[start_time, end_time]`.

### Decisive source
```python
# litellm_logging.py:3028-3044 (abridged)
# on some exceptions, model_call_details is not always initialized, this ensures that we still log those exceptions
if not hasattr(self, "model_call_details"):
    self.model_call_details = {}
...
self.model_call_details["traceback_exception"] = (
    _redact_string(traceback_exception) if isinstance(traceback_exception, str) else traceback_exception
)
...
# A stream interrupted mid-flight still billed the provider for the chunks already delivered;
# the router stashes that recovered usage as ``combined_usage_object`` and pre-computes its cost,
# so preserve it here instead of zeroing the spend on an otherwise-failed request.
if self.model_call_details.get("combined_usage_object") is None:
    self.model_call_details["response_cost"] = 0
```

**Flow:** normalize times → ensure `model_call_details` exists (failures before init still log) → stamp `log_event_type="failed_api_call"` + exception + redacted traceback → zero `response_cost` ONLY when no recovered `combined_usage_object` exists → merge `exception.headers` dict into `litellm_params.metadata` → build standard payload with `status="failure"` and redacted `error_str`.
**Invariant:** Tracebacks and error strings are redacted at THIS layer (before any sink), and a failed-but-billed stream keeps its recovered spend instead of being zeroed.
**Probe:** covered by the same live suites above (failure path exercised via `dispatch_failure_handlers` tests, 8 passed live — see async-twins capsule); no separate direct test read this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "should_run_callback _success_handler_helper_fn _failure_handler_helper_fn",
  filePattern: "litellm_logging.py", limit: 20 });
// → rank-1..n surface the gate (:1875), both helpers (:2047/:3022), and the twin call sites (:2274/:2760)
```

## Verdict
Adopt the per-callback gate with its operator kill-switch first and the cost-tracking carve-out last; adopt the shared-helper shape (one normalization function serving sync and async bodies) and the four-rung cost ladder with its zero-vs-positive asymmetry; adopt fail-before-init tolerance in the failure helper. Adapt the `_PROXY_` class-name convention to your own cost-tracker marker (a capability flag would be cleaner but changes the contract). Omit the enterprise header-disable rung unless you have a multi-tenant control plane. Coverage caveat: the direct no-log test lives in `tests/local_testing/**` (vcr-blocked this session); all cited helper behavior was confirmed by source read plus the four live-passing tests named above.
