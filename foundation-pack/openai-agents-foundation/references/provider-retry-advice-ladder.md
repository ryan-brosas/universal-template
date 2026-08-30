<!-- capsule-v2 -->
# Provider retry-advice ladder — how does a model adapter classify a failed request BEFORE the runner's veto machinery?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** Given a raw provider exception, when should a model adapter say retry / no-retry / unsafe-to-replay, and which signals dominate?

## Advice derivation over a normalized error
**Path/Symbol:** `src/agents/models/_openai_retry.py:` `get_openai_retry_advice` (:41–112); helpers in `src/agents/models/_retry_runtime.py` (`iter_error_chain`, `get_retry_after`, header/status/code extraction); advice types in `src/agents/retry.py` (`ModelRetryAdvice`, `ModelRetryAdviceRequest`, `ModelRetryNormalizedError` :49–113).
**Signature:** `def get_openai_retry_advice(request: ModelRetryAdviceRequest) -> ModelRetryAdvice | None`.
**Data Shape:** request carries `error, attempt, stream, previous_response_id?, conversation_id?`; advice carries `suggested, retry_after, replay_safety ("safe"/"unsafe"/None→unknown), reason, normalized, response_started`.

### Decisive source
```python
if getattr(error, "unsafe_to_replay", False):
    return ModelRetryAdvice(suggested=False, replay_safety="unsafe", ...)
if "...the sdk will not automatically retry this websocket request." in error_message:
    return ModelRetryAdvice(suggested=False, replay_safety="unsafe", ...)
retry_after = get_retry_after(error)
normalized = _build_normalized_error(error, retry_after=retry_after)   # walks the error chain
should_retry_header = _get_header_value(error, "x-should-retry")
if should_retry_header is not None:
    if should_retry_header.lower().strip() == "true":
        return ModelRetryAdvice(suggested=True, retry_after=retry_after, replay_safety="safe", ...)
    if should_retry_header.lower().strip() == "false":
        return ModelRetryAdvice(suggested=False, ...)                  # absolute no
if normalized.is_network_error or normalized.is_timeout:
    return ModelRetryAdvice(suggested=True, ...)
if normalized.status_code in {408, 409, 429} or (isinstance(normalized.status_code, int) and normalized.status_code >= 500):
    advice = ModelRetryAdvice(suggested=True, ...)
    if stateful_request:            # previous_response_id/conversation_id present
        advice.replay_safety = "safe"
    return advice
if retry_after is not None:
    return ModelRetryAdvice(retry_after=retry_after, ...)   # suggested stays None = no opinion
return None
```

**Flow:** explicit replay-unsafe markers first → server `x-should-retry` header is absolute authority while present → network/timeout (anywhere in the exception chain) always retriable → transient status codes retriable, upgraded to `replay_safety="safe"` for stateful requests → bare `retry_after` forwards timing without an opinion → otherwise `None` (no advice; runner defaults decide).
**Invariant:** the adapter never retries anything itself; it classifies. `unsafe_to_replay` and the websocket-accepted message are non-overridable "unsafe" verdicts that downstream veto logic turns into hard stops; header true/false beats every heuristic below it. Normalization marks `is_network_error`/`is_timeout` by walking the WHOLE chain (`APIConnectionError`/`APITimeoutError`), not just the outer exception.
**Probe:** `tests/models/test_openai_retry_helpers.py::test_advice_respects_x_should_retry_false` (:173), `::test_advice_unsafe_to_replay` (:150), `::test_advice_returns_retry_after_only_when_no_other_signal` (:182).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "get_openai_retry_advice" }); // live ladder retrieved this pass
```

## Verdict
Adopt the ordering: unsafe markers → header authority → chain-walked network/timeout → transient statuses (+stateful-safe upgrade) → retry-after-only. Adapt status-code sets and header names per provider. Omit the runner-side veto trio (already mined as model-retry-veto-trio). Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
