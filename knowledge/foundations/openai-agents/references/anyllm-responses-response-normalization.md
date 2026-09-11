<!-- capsule-v2 -->
# AnyLLM Responses response normalization — how does an adapter turn provider Responses payloads and streams into honest SDK outputs?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** How does a multi-provider adapter validate/normalize non-stream Responses payloads, and how does its stream path keep usage honest (no synthesized zeros), record spans before the terminal yield, and still deliver terminal failure events to the consumer?

## Response-side plane
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_get_response_via_responses` (:373–453), `_stream_response_via_responses` (:455–557), `_normalize_response` (:1241–1259); `src/agents/usage.py:` `_mark_request_completed_without_usage` (:318–328), `_requests_for_response_without_usage` (:334–343), `_response_usage_to_usage` (:346+).
**Signature:** `def _normalize_response(self, response: Any) -> Response`; `async def _stream_response_via_responses(...) -> AsyncGenerator[ResponseStreamEvent, None]`.
**Data Shape:** provider payload may be a `Response`, a pydantic `BaseModel`, or a raw dict; stream chunks are `ResponseStreamEvent`s; usage may be absent on any provider; `model_settings.preserve_raw_usage` gates raw-usage snapshot attachment.

### Decisive source
```python
# _normalize_response: passthrough → dump → cache_write_tokens backfill
if isinstance(response, Response):
    return response
payload = response.model_dump() if isinstance(response, BaseModel) else response
if isinstance(payload, dict):
    usage = payload.get("usage")
    if isinstance(usage, dict):
        input_tokens_details = usage.get("input_tokens_details")
        if (isinstance(input_tokens_details, dict)
                and "cache_write_tokens" not in input_tokens_details):
            payload = {**payload, "usage": {**usage,
                "input_tokens_details": {**input_tokens_details, "cache_write_tokens": 0}}}
return Response.model_validate(payload)
```
and the stream's terminal handling:
```python
elif chunk_type in {"response.failed", "response.incomplete"}:
    terminal_failure_error = response_terminal_failure_error(...)
elif chunk_type in {"error", "response.error"}:
    terminal_failure_error = response_error_event_failure_error(...)
if chunk_type in {"response.completed", "response.failed", "response.incomplete",
                  "error", "response.error"}:
    yielded_terminal_event = True
    # span usage + response + error record populated BEFORE the yield
    ...
    yield chunk
...
if terminal_failure_error is not None:
    raise terminal_failure_error   # only after the loop; a consumer that stopped at the
                                   # terminal event already saw the failure as data
```

**Flow:** non-stream — `status in {"failed", "incomplete"}` raises `ModelBehaviorError` via `response_terminal_failure_error` before any output read; usage built with `requests=1` and provider fields, or `Usage(requests=1)` when the provider omits usage entirely (request counted, tokens never synthesized as zeros); span usage set via `model_usage_to_span_usage`; span response/input only when `tracing.include_data()`; raw-usage snapshot attached only under `preserve_raw_usage`. Stream — `ResponseCompletedEvent` captures `final_response`, attaches raw usage, and marks usage-less completions with `_mark_request_completed_without_usage` so `_requests_for_response_without_usage` later counts exactly one request (default 0 unless an adapter opted in); failure/error events are recorded AND still yielded; span population and error recording happen before the terminal yield; `CancelledError` schedules a background close and re-raises; the `finally` closes the stream allowing an in-flight close to finish in the background; cleanup errors after a yielded terminal event are logged-and-swallowed, before it they re-raise.

**Invariant:** (1) A completed request always counts as one request — with or without provider usage; token counts are never fabricated. (2) Terminal failure events are data first (yielded) and exception second (raised only if the consumer kept iterating). (3) A consumer that stops at the terminal event still leaves a fully recorded span (usage, response, error). (4) `_normalize_response` never mutates the provider object; pydantic-required `cache_write_tokens` is backfilled to 0 on a copied payload.

**Probe:** `tests/models/test_any_llm_model.py` — `test_any_llm_responses_path_rejects_failed_terminal_status` (:830, parametrized failed/incomplete), `test_any_llm_responses_stream_rejects_failed_terminal_events` (:1072, event yielded then raised), `test_any_llm_responses_stream_rejects_error_event` (:1112), `test_any_llm_responses_stream_populates_span_before_yielding_completed` (:2111), `test_any_llm_responses_stream_ignores_close_failure_after_terminal_event` (:1956) / `..._after_terminal_failure` (:1971) / `..._propagates_close_failure_before_terminal_event` (:1995), `test_any_llm_responses_stream_closes_provider_stream_after_cancellation` (:2023), `test_any_llm_responses_stream_lets_in_flight_close_finish_after_cancellation` (:2177).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "normalize responses payload stream terminal failure event usage without usage span before yield", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the usage-honesty ladder (requests=1 without usage; explicit no-usage marker instead of zero-filled tokens) and the yield-then-raise terminal-event contract with span-before-yield — both port cleanly to any streaming adapter. Adapt `_normalize_response`'s backfill list to your pydantic schema's required-without-default fields. Omit the any-llm-specific provider caching/retry-clone plumbing (covered by anyllm-provider-plane.md). Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
