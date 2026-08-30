<!-- capsule-v2 -->
# AnyLLM transport kwargs, replay sanitization, and stream close discipline — how do transport-level options and replayed items cross a validating upstream, and how are provider streams closed under cancellation?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How does the adapter pass OpenAI transport kwargs (extra_headers/query/body) through any-llm's public API that rejects them, sanitize replayed Responses input for upstream validation, and guarantee provider stream cleanup on cancellation?

## Private-API split + recursive sanitizer + shielded close
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_call_any_llm_responses` (:1395–1434), `_make_any_llm_responses_params` (:1436–1443), `_AnyLLMResponsesParamsShim` (:94–104), `_sanitize_any_llm_responses_input`/`_sanitize_any_llm_responses_value` (:1445–1490), `_build_responses_transport_kwargs` (:1388–1393), `_close_stream_allowing_background_completion` (:1332–1346), `_detach_stream_close` (:1347–1352), `_consume_background_cleanup_task_result` (:1354–1361), `stream_response` `aclosing` forwarding (:349–371).
**Signature:** `_call_any_llm_responses(*, request_kwargs: dict, transport_kwargs: dict) -> Response | AsyncIterator[ResponseStreamEvent]`; `_sanitize_any_llm_responses_value(self, value: Any) -> Any | None`.
**Data Shape:** `request_kwargs` split into `_ANY_LLM_RESPONSES_PARAM_FIELDS` (public params) vs the rest; `transport_kwargs` (extra_headers/extra_query/extra_body) merged over provider kwargs; sanitizer returns `None` to DROP an item.

### Decisive source
```python
# any-llm 1.11.0 validates public `aresponses()` kwargs against ResponsesParams,
# which rejects OpenAI transport kwargs like `extra_headers`. Build the params
# model ourselves so we can still pass transport kwargs through to the provider.
response = await provider._aresponses(
    self._make_any_llm_responses_params(params_payload), **provider_kwargs)

# sanitizer: drop, don't fail
if value.get("type") == "reasoning" and value.get("provider_data"):
    return None                      # provider-specific reasoning is not replay-safe
if key == "id" and item_value == FAKE_RESPONSES_ID:
    continue                         # SDK-synthesized ids never cross the boundary
if item_value is None:
    continue                         # explicit nulls rejected by upstream models
```

**Flow:** responses-path calls with transport kwargs bypass the public `aresponses` and call the private `provider._aresponses` with a self-built `ResponsesParams` (import-fail fallback: local shim with `model_dump(exclude_none=True)`) so headers/query/body still reach the provider → every replayed input item is recursively sanitized: `provider_data` keys stripped, `FAKE_RESPONSES_ID` ids dropped, None values dropped, reasoning items carrying provider_data dropped entirely — items are removed, never error → stream lifecycle: `stream_response` wraps the delegate generator in `contextlib.aclosing` so an early `aclose()` on the SDK generator deterministically closes the delegate; the guarantee deliberately STOPS at the any-llm iterator (its wrappers use bare `async for` and do not forward `aclose` — upstream concern) → when cancellation arrives while `aclose()` is already awaiting the provider, `_close_stream_allowing_background_completion` shields the close task and detaches it on `CancelledError`, letting the in-flight close finish in the background instead of abandoning it half-done or starting a second (non-idempotent) close; the detached task's result is consumed by done-callback (CancelledError swallowed, other errors logged debug).
**Invariant:** transport kwargs reach the provider even through a validating public API (private-API escape documented, not hidden); replay sanitization is subtractive-only — it can drop content but never raises or fabricates; a provider stream is closed exactly once and cancellation never leaves a half-closed iterator or an unconsumed task exception.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_responses_path_passes_transport_kwargs_via_private_provider_api` (:1150), `::test_any_llm_responses_path_sanitizes_replayed_items_before_validation` (:1243), `::test_any_llm_chat_stream_closes_provider_stream_after_cancellation` (:1861), `::test_any_llm_chat_stream_lets_in_flight_close_finish_after_cancellation` (:2138), `::test_any_llm_responses_stream_ignores_close_failure_after_terminal_event` (:1956).
