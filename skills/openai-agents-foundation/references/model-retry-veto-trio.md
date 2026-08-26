<!-- capsule-v2 -->
# Model-retry veto trio — under which conditions is a failed model request FORBIDDEN from being retried regardless of policy?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Which replay-safety vetoes override an application's retry policy, and how do the three approval paths differ?

## Absolute vetoes + three approval lanes
**Path/Symbol:** `src/agents/run_internal/model_retry.py:` `_evaluate_retry` (:278–382), `_normalize_retry_error` (:110–150), `_default_retry_delay` (:169–198).
**Signature:** `async def _evaluate_retry(*, error, attempt, max_retries, retry_policy, retry_backoff, stream, replay_unsafe_request, emitted_retry_unsafe_event, provider_advice, previous_response_id=None, conversation_id=None) -> RetryDecision`.
**Data Shape:** normalized error carries status/code/message/request_id/retry_after + booleans `is_abort`, `is_network_error`, `is_timeout`; decisions carry `retry`, `delay`, `reason`, private `_approves_replay`, and public `approve_unsafe_replay`.

### Decisive source
```python
# Aborts, and failures that already emitted user-visible streamed output, are absolute
# vetoes. No application decision can make replaying those safe.
if normalized.is_abort or emitted_retry_unsafe_event:
    return RetryDecision(retry=False, ...)
...
if replay_unsafe_request and not decision._approves_replay and not provider_marks_replay_safe:
    return RetryDecision(retry=False, ...)   # 1. request-level local side effects
if stateful_request and not (
    decision._approves_replay or provider_marks_replay_safe
    or (decision.approve_unsafe_replay and provider_marks_replay_unsafe)
):
    return RetryDecision(retry=False, ...)   # 2. stateful requests fail closed by default
if provider_marks_replay_unsafe and not (
    decision._approves_replay or decision.approve_unsafe_replay
):
    return RetryDecision(retry=False, ...)   # 3. provider-unsafe failure needs explicit approval
```
Delay precedence when retry IS allowed: policy-provided delay → provider `retry_after` → default backoff `min(initial·m^(n-1), max)` with ±12.5% jitter clamped ≥0.

**Flow:** budget gate (`attempt > max_retries` ⇒ stop) → normalize (provider advice may override fields EXCEPT it can only ADD abort evidence, never clear it) → absolute vetoes → stream+unsafe short-circuit BEFORE the policy runs → run policy → enforce the three vetoes → compute delay. Provider normalization may add abort evidence but cannot clear abort inferred from the raw exception.

**Invariant:** An ordinary `retry=True` approves nothing: request-local side effects need `_approves_replay`; stateful requests need provider-marked safety or scoped `approve_unsafe_replay`; unknown replay-safety stays BLOCKED (an approval must be about a known unsafe failure). Streamed output already shown to the user can never be re-requested.

**Probe:** `tests/test_agent_runner.py::test_non_streamed_model_retry_does_not_rewind_committed_session_input` (:3454) and streamed twin :485 in test_agent_runner_streamed.py pin committed-input non-rewind; conversation-locked fixtures at :3418–3425.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "evaluate retry veto approve unsafe replay stateful", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the veto hierarchy verbatim for any LLM call path with side-effectful tools or server-managed state; adapt the advice/override plumbing to your error taxonomy; omit websocket pre-event toggles if you have no WS transport.
