<!-- capsule-v2 -->
# Three-shape completion callback — how do you accept sync, async, AND async-generator callbacks without silently dropping any form?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What dispatch ladder accepts every reasonable user callback shape (`on_complete`/`on_cancel`) and yields the events generators produce?

## _dispatch_callback ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `_dispatch_callback` (:379–400); type aliases `OnCompleteFunc`/`OnCancelFunc` (:83–93) = `_CallbackFunc[AgentRunResult, EventT] | _CallbackFunc[RunCancelled, EventT]`; helpers `_utils.is_async_callable` (:775+), `_utils.run_in_executor` (:183–200).
**Signature:** `async def _dispatch_callback(self, callback: _CallbackFunc[_CallbackArgT, EventT], arg: _CallbackArgT) -> AsyncIterator[EventT]`.
**Data Shape:** accepted forms: async-gen function → events; async callable (coroutine fn or callable-object with coroutine `__call__`) → None; plain callable returning AsyncIterator | Awaitable | anything.

### Decisive source
```python
if inspect.isasyncgenfunction(callback):
    # Fast path for the common `async def ... yield` form.
    async for event in callback(arg): yield event
elif _utils.is_async_callable(callback):
    await callback(arg)
else:
    # A plain callable can still return an async iterator or awaitable that neither
    # `isasyncgenfunction` nor `is_async_callable` detects (a `def` that returns an
    # async generator, or a callable instance whose `__call__` is an async generator).
    # Run it off-thread in case it's blocking-sync, then honour whatever it returned ...
    result = await _utils.run_in_executor(callback, arg)
    if isinstance(result, AsyncIterator):
        async for event in result: yield event
    elif inspect.isawaitable(result):
        await result
```

**Flow:** cheapest introspection first (asyncgen function) → coroutine-style await → everything else runs in an executor thread whose RETURN VALUE is then honored (AsyncIterator drained, awaitable awaited, other values dropped).
**Invariant:** three rules:
1. The third branch must run the callable OFF-THREAD even though its result may be async — a blocking `def` callback would otherwise stall the event loop; and its result must still be honored or generator-forms defined as plain functions get "silently dropped".
2. Order matters: `isasyncgenfunction` before `is_async_callable` — an async generator function is also an async callable, but awaiting it returns an unusable async-generator object instead of draining it.
3. Callbacks fire at exactly one site each: `on_complete` only on AgentRunResultEvent, `on_cancel` only in the RunCancelled branch BEFORE the `on_cancelled()` hook — so a cancel produces callback events then hook events, in that order.
**Probe:** `.venv/bin/python -m pytest 'tests/test_ui.py::test_run_stream_on_cancel' 'tests/test_ui.py::test_run_stream_on_cancel_not_called_for_success_or_error' -p no:cacheprovider` (anchored at repo root; pins async-gen `on_cancel` receiving the SAME `RunCancelled` object later exposed via `.cancelled`, and zero invocations on success/plain-error).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_dispatch_callback isasyncgenfunction run_in_executor", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-shape ladder verbatim wherever user callbacks can append protocol events (webhook systems, pipeline hooks); adapt the argument type; omit the executor branch ONLY if you control all callbacks in-tree.
