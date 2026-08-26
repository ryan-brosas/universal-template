<!-- capsule-v2 -->
# Sync hooks on threads + abandon-on-cancel — how do you give blocking sync callbacks a real timeout?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Why does `anyio.fail_after` alone fail to time out a sync hook, and what makes it actually raise?

## sync-hook-timeout-dispatch
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/capabilities/hooks.py:` `_call_entry` timeout branch (:241–252), `_call_func` (:254–260); machinery in `_utils.py`: `_abandon_on_cancel` ContextVar (:78–80), `abandon_threads_on_cancel` ctx mgr (:162–174), `run_in_executor` passing `abandon_on_cancel=_abandon_on_cancel.get()` to anyio's `run_sync`.
**Signature:** `with anyio.fail_after(entry.timeout), _utils.abandon_threads_on_cancel():` — the two context managers are INSEPARABLE at every timed call site.
**Data Shape:** `_call_func` routes by callable shape: `is_async_callable(func)` → direct await; plain `def` → `await _utils.await_maybe(await _utils.run_in_executor(func, *args))` (a sync def may RETURN an awaitable, which the thread dispatch alone would leave un-awaited).

### Decisive source
```python
# _utils.py comment (load-bearing):
# Any cancellation delivered while awaiting a worker thread abandons that thread, not just the one a
# deadline schedules: `anyio` cannot tell them apart. That is acceptable only because this dial is set
# tightly around calls that are already armed with a deadline, whose owner asked for a timeout.

async def _call_func(func, *args, **kwargs):
    """Call a function, running sync functions in a thread so they don't block the event loop."""
    if _utils.is_async_callable(func):
        return await func(*args, **kwargs)
    return await _utils.await_maybe(await _utils.run_in_executor(func, *args, **kwargs))
```

**Flow:** timed hook → `fail_after` arms deadline + `abandon_threads_on_cancel` flips the dial → sync hook dispatched to worker thread with abandon enabled → thread overruns deadline → cancel arrives at the await → anyio ABANDONS the thread (it keeps running to completion, result discarded) instead of shielding until it returns → TimeoutError converts to `HookTimeoutError(hook_name, timeout)` with the original as `__cause__`.
**Invariant:** four rules:
1. Default anyio behavior SHIELDS the await — cancellation is delivered only after the thread returns, so `fail_after` alone cannot enforce a deadline against a blocking sync callback. Abandonment is what makes the timeout real.
2. Thread abandonment loses work silently — acceptable ONLY when scoped tightly around calls whose owner explicitly armed a deadline. Never flip the dial globally.
3. Async detection must use `is_async_callable` (handles functools.partial of async fns), and the sync path must STILL await the result (`await_maybe`) because plain defs can return awaitables.
4. Timeout conversion preserves the chain: `except TimeoutError: raise HookTimeoutError(...) from e`.
**Probe:** `tests/test_capabilities.py` pins HookTimeoutError + timeout semantics (grep `HookTimeoutError` hits tests/test_capabilities.py); `tests/test_utils.py` covers `is_async_callable`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "abandon_threads_on_cancel fail_after HookTimeoutError run_in_executor sync hook timeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the paired-context-manager idiom (deadline + abandon dial) anywhere you enforce timeouts on foreign sync code; adapt the exception type; omit the abandon dial only where losing the thread's work is unacceptable even under a deadline.
