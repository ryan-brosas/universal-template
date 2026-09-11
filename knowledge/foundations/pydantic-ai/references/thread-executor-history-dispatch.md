<!-- capsule-v2 -->
# Bounded thread-executor swap + sync/async history-processor dispatch — run-scoped executor context and the four-shape callable ladder

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/thread_executor.py` + `capabilities/process_history.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you bound the threads used for sync tools/callbacks in long-running servers, and how do you invoke a user history processor that may be any of {sync, async} × {takes-ctx, no-ctx} without leaking un-awaited coroutine returns? A porter will feed a plain-def-returning-awaitable into an executor and drop its future.

## Path / Symbol
`thread_executor.py` — `UseThreadExecutor(AbstractCapability)` (:16–55): `wrap_run` opens `_utils.using_thread_executor(self.executor)` around `handler()` (:48–55); deprecated `ThreadExecutor` alias via module `__getattr__` + PydanticAIDeprecationWarning (:58–72). `process_history.py` — `ProcessHistory(AbstractCapability)` (:25–42) delegating to `_run_history_processor` (:45–63).

## Signature
```python
async def wrap_run(self, ctx, *, handler: WrapRunHandler) -> AgentRunResult[Any]:
    with _utils.using_thread_executor(self.executor):
        return await handler()

async def _run_history_processor(processor, ctx, messages) -> list[ModelMessage]:
    takes_ctx = takes_run_context(processor)
    if is_async_callable(processor): ... # direct await, ctx-or-not
    else: return await await_maybe(await run_in_executor(...))  # plain def MAY still return an awaitable
```

## Data Shape
HistoryProcessorFunc = 4-shape union: `(ctx, messages) | (messages)` × `sync | async`, all returning `list[ModelMessage]` (or awaitable thereof). The executor capability is per-agent (`capabilities=[UseThreadExecutor(executor)]`) or global (`Agent.using_thread_executor()`); default remains `anyio.to_thread.run_sync` ephemeral threads.

### Decisive source
The awaitable-after-executor trap (:59–61):
```python
else:
    # A plain `def` may still return an awaitable, which `run_in_executor` would leave un-awaited.
    if takes_ctx:
        return await await_maybe(await run_in_executor(cast('_SyncWithCtx', processor), ctx, messages))
```

**Flow:** Executor: the capability wraps the WHOLE run so every sync tool/callback dispatched inside resolves its thread pool from the ambient context instead of spawning ephemeral threads — bounded workers prevent thread accumulation under sustained FastAPI-style load. History processing happens in `before_model_request`; replacement list is assigned back onto `request_context.messages`.

**Invariant:** Sync-in-event-loop offloading must honor the scoped executor; dispatch on (is_async, takes_ctx) BEFORE choosing the execution vehicle, and always `await_maybe` the result of anything that ran in an executor.

**Probe:** `tests/test_capabilities.py` — serialization-name + deprecation alias pins (:15734/:15742/:15747), functional executor test (:15760 agent runs with UseThreadExecutor(executor)). `tests/test_history_processor.py` — all four shapes exercised (:69/:79/:134/:200/:268); delta-strip/rebuild twins at test_capabilities.py :3836/:3875/:16845.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'UseThreadExecutor ProcessHistory _run_history_processor using_thread_executor'
```

## Verdict
**Adopt** the run-scoped executor context and the four-shape dispatch ladder with await_maybe. **Adapt** the deprecation shim only if you carry a renamed public symbol. **Omit** ProcessHistory entirely if your host has no history-transformation hook — but keep the dispatch lesson for ANY user-callable surface.
