<!-- capsule-v2 -->
# Retry-with-status wrapper — how do you keep users informed during LLM backoff without coupling the retry policy to the UI?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** rate-limited or transiently-failing model calls go silent for the whole backoff window — how does a PipesHub-specific SSE status ride the generic retry ladder?

## PRE_MODEL_CALL wrap middleware emitting before each sleep
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/retry_with_status.py:57-103` (`retry_with_status`, wired `hooks.wrapper(HookEvent.PRE_MODEL_CALL).use(...)` at `factory.py:912`); `_is_retryable` :34-44, `_retry_status_message` :47-54.
**Signature:** `retry_with_status(event_sink: EventSink | None, config: RetryConfig | None = None) -> WrapMiddleware[ModelResponse]`.
**Data Shape:** consumes `TransportError(status_code, retryable)`; emits `{"event":"status","data":{"status":"retrying","message":...}}`; backoff `delay = min(delay * backoff_factor, max_delay)` + `random.uniform(0, delay*0.1)` jitter.

### Decisive source
```python
for attempt in range(cfg.max_retries + 1):
    try:
        return await next_fn()
    except TransportError as exc:
        if not _is_retryable(exc, cfg) or attempt >= cfg.max_retries:
            raise
        last_exc = exc
        if event_sink is not None:
            try:
                await event_sink.write({... "retrying" ...})
            except Exception:
                logger.debug("retry_with_status: event_sink.write failed", exc_info=True)
        await asyncio.sleep(delay + jitter)
        delay = min(delay * cfg.backoff_factor, cfg.max_delay)
```

**Flow:** each attempt → on non-retryable OR exhausted → re-raise untouched → else emit status BEFORE sleeping (so the frontend spinner shows progress instead of a hang) → exponential backoff with jitter.
**Invariant:** this lives in the adapter layer, NOT agent_loop_lib, because EventSink/SSE shapes are product-specific — the kernel's RetryHook has no stream concept. `_is_retryable` is deliberately duplicated from `retry.py` rather than imported so this module depends only on shared types. Sink-write failures are swallowed (debug log) — a broken SSE channel must never break a real retry. `event_sink=None` (background runs) silently skips emission and still retries. 529 counts as retryable under default config.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_retry_with_status.py::test_raises_after_exhausting_max_retries` (:85) — asserts calls==3 AND exactly 2 status events ("before each retry, none after the final raise"); `.test_event_sink_write_failure_does_not_break_retry` :125; `.test_529_overloaded_is_retried_under_default_config` :141. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_retry_with_status.py -q` (9 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "retry_with_status TransportError backoff event_sink status", limit: 4, fields: ["signature", "name", "file"] });
// resolves hooks/retry_with_status.py cluster line-exact
```

## Verdict
Adopt the wrap-middleware shape for product-specific observability around a generic retry ladder (emit-before-sleep, fail-open sink writes, None-sink tolerance). Adapt status payload and message copy to your SSE vocabulary. Omit agent_loop_lib's own RetryHook when your control plane doesn't wire it.
