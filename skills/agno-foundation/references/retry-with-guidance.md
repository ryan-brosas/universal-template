<!-- capsule-v2 -->
# Retry-with-guidance — how do you retry a model call by TEACHING it instead of just sleeping?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** How does a provider error that extra instructions could fix get retried differently from a transient 5xx?

## Model._invoke_with_retry
**Path/Symbol:** `libs/agno/agno/models/base.py:231` (async twin `_ainvoke_with_retry` :279; stream twin `_invoke_stream_with_retry` :328 — retries RESTART the entire stream, :333 comment).
**Signature:** `_invoke_with_retry(self, **kwargs) -> ModelResponse`; knobs: `retries: int = 0`, `delay_between_retries: int = 1`, `exponential_backoff: bool = False`, `retry_with_guidance: bool = True`, `retry_with_guidance_limit: int = 1`.
**Data Shape:** two DISTINCT retryable error classes drive two distinct loops — plain `ModelProviderError` (transient) and `RetryableModelProviderError` (guidance-carrying dataclass with `original_error` + `retry_guidance_message`).

### Decisive source
```python
for attempt in range(self.retries + 1):
    try:
        return self.invoke(**kwargs)
    except ModelProviderError as e:
        last_exception = self.classify_error(e)              # subclassify first
        if not self._is_retryable_error(last_exception):
            raise last_exception from e                      # non-retryable: NO sleep, raise NOW
        if attempt < self.retries:
            delay = self.delay_between_retries * (2**attempt) if self.exponential_backoff \
                    else self.delay_between_retries
            sleep(delay)
    except RetryableModelProviderError as e:
        current_count = retries_with_guidance_count          # threaded through kwargs
        if current_count >= self.retry_with_guidance_limit:
            raise ModelProviderError(message=f"Max retries with guidance reached. Error: {e.original_error}", ...)
        kwargs.pop("retry_with_guidance", None)
        kwargs["retries_with_guidance_count"] = current_count + 1
        # THE move: append guidance as a TEMPORARY user message, then recurse
        kwargs["messages"].append(Message(role="user", content=e.retry_guidance_message, temporary=True))
        return self._invoke_with_retry(**kwargs, retry_with_guidance=True)
raise last_exception
```
Retryability gate (`_is_retryable_error` :203-229): `ContextWindowExceededError` ⇒ never; status ∈ {400,401,403,404,413,422} ⇒ never; message matching any `ModelProviderError.CONTEXT_WINDOW_PATTERNS` ⇒ never (defense-in-depth for unclassified errors); everything else (429, 5xx, unknown) ⇒ retryable.

**Flow:** invoke → on classified-transient error: backoff sleep → same call again → on guidance error: append temporary user message carrying the fix instructions → recurse immediately (no sleep) → limit exceeded converts to generic ModelProviderError.
**Invariant:** (1) The guidance message is marked `temporary=True` so downstream layers (fallback stripping :128, history persistence) exclude it — the model sees it ONCE, the transcript never stores it. (2) The guidance counter travels inside kwargs because the recursion re-enters through the public wrapper. (3) Non-retryable raises IMMEDIATELY without consuming sleeps. (4) Stream retries restart from byte zero — partial streams are discarded.
**Probe:** graph-resolves line-exact (`search_graph "_invoke_with_retry retry_with_guidance"` → base.py:231-277); retryability matrix mirrored by upstream `tests/unit/test_fallback.py::test_get_fallback_models_blocks_400_bad_request` family (executed GREEN); no dedicated unit file for the guidance path — recorded caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "Model._invoke_with_retry retry_with_guidance", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-loop split (sleep-retry vs teach-retry) and the temporary-message mechanism; adapt the guidance-message injection point to your prompt plumbing; omit agno's specific classify() patterns if your providers raise typed errors already. Caveat: no direct unit test pins the guidance recursion itself.
