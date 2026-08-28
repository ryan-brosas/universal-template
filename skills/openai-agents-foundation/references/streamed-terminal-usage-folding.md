<!-- capsule-v2 -->
# Streamed terminal-response assembly — how does a streamed turn turn the terminal event into a ModelResponse, and how do failed retry attempts reach token accounting without double counting?

**Source:** openai-agents-python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** A porter streaming from a chunk-based provider must know how the terminal response is assembled, what rescue rules apply when the terminal payload is incomplete, and how failed attempts are folded into usage on both paths.

## Terminal-response assembly and retry-usage folding
**Path/Symbol:** `src/agents/run_internal/run_loop.py:run_single_turn_streamed` terminal block (:2240–2313); `src/agents/run_internal/model_retry.py:apply_retry_attempt_usage` (:338–352) and `get_response_with_retry` (:613).
**Signature:** `def apply_retry_attempt_usage(usage: Usage, failed_attempts: int) -> Usage`; streamed terminal block builds `ModelResponse(output, usage, response_id, request_id, raw_usage)`.
**Data Shape:** Terminal `Response` from `ResponseCompletedEvent`; accumulated `streamed_response_output: list[ResponseOutputItem]` from `ResponseOutputItemDoneEvent`; `stream_failed_retry_attempts: list[int]` (mutable cell) filled by `stream_response_with_retry`.

### Decisive source
```python
if is_completed_event and not terminal_response.output and streamed_response_output:
    # Some streaming backends emit output items during item.done events while
    # leaving the terminal response output empty. Preserve those items so the
    # runner can resolve the completed step correctly.
    terminal_response.output = list(streamed_response_output)
usage = apply_retry_attempt_usage(
    (_response_usage_to_usage(terminal_response.usage) if terminal_response.usage
     else Usage(requests=_requests_for_response_without_usage(terminal_response))),
    stream_failed_retry_attempts[0],
)
```
```python
def apply_retry_attempt_usage(usage: Usage, failed_attempts: int) -> Usage:
    if failed_attempts <= 0:
        return usage
    successful_request_entries = list(usage.request_usage_entries)
    if not successful_request_entries:
        successful_request_entries.append(_build_request_usage_entry_from_usage(usage))
    usage.requests = max(usage.requests, 1) + failed_attempts
    usage.request_usage_entries = [
        _build_zero_request_usage_entry() for _ in range(failed_attempts)
    ] + successful_request_entries
    return usage
```

**Flow:** (1) events stream through `aclosing(model_run_context_stream(retry_stream, ...))`; `response.incomplete`/`response.failed`/`error` events raise immediately via `response_terminal_failure_error`/`response_error_event_failure_error`; (2) `ResponseOutputItemDoneEvent` items accumulate into `streamed_response_output`; (3) on the completed event an empty terminal output is rescued from the accumulated items; (4) usage is converted, or synthesized with `_requests_for_response_without_usage` when the terminal response omits usage (adapters folding several provider responses into one report counts separately and must not be double-counted); (5) `apply_retry_attempt_usage` folds failed attempts: zero-usage entries are PREPENDED (failed attempts keep chronological first position), `requests` becomes `max(requests, 1) + failed_attempts`; (6) `final_response is None` after the loop raises `ModelBehaviorError("Model did not produce a final response!")`; (7) `usage.add(final_response.usage)` at :2306, then the post-success tracker re-mark trio (`mark_input_as_sent`/`mark_input_as_accepted`/`track_server_items`, :2311–2313) mirrors the non-streamed `get_new_response` tail.
**Invariant:** Failed retry attempts are never silently dropped from token accounting (the streamed path would otherwise diverge from `get_response_with_retry`, which applies the same fold at :613), and a successful retry restores exactly the delivered-input tracking state the next turn's delta computation expects.
**Probe:** `tests/test_agent_runner_streamed.py::test_streamed_run_preserves_request_usage_entries_after_retry` (:405) and `::test_streamed_run_counts_retry_attempts_when_terminal_usage_missing` (:449); `tests/models/test_any_llm_model.py::test_any_llm_responses_stream_counts_request_when_usage_is_absent` (:2218).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "apply_retry_attempt_usage stream_failed_retry_attempts ResponseCompletedEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the terminal-assembly ladder (rescue accumulated items, synthesize zero-usage requests, prepend failed-attempt entries, fail loud when no terminal response) and the post-success tracker re-mark trio. Adapt the mutable-cell retry counter to your retry helper's shape. Omit the OpenAI-specific event-type names only if your provider has an equivalent terminal taxonomy — otherwise keep the raise-on-incomplete/failed/error behavior. Coverage caveat: MCP not connected this pass; anchors verified by direct reads at HEAD fe45b415.
