<!-- capsule-v2 -->
# FunctionModel callable instances — when does a user-supplied model callable run on the event loop vs a worker thread, and what does its absence of `__name__` change?

**Source:** pydantic-ai MIT `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03` (commit 855f441 "Accept any callable as a FunctionModel function or stream_function" #7589); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter replacing the async predicate with plain `inspect.iscoroutinefunction` (or skipping the name fallback) breaks executor routing or name generation for stateful test doubles — what exactly must dispatch on?

## Callable-instance routing + naming contract
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/function.py:FunctionModel.__init__` (:128-136) and `.request` (:166-174); helpers `_utils.py:is_async_callable` (:775-786) and `_utils.py:await_maybe` (:787-800); custom-executor seam `_utils.py:using_thread_executor` (:137-159) consumed by `run_in_executor` (:183-205).
**Signature:** `FunctionModel(function=None, *, stream_function=None, model_name=None, profile=None, settings=None)`; `FunctionDef = Callable[[list[ModelMessage], AgentInfo], ModelResponse | Awaitable[ModelResponse]]` — docstring (:307-311) now states "Any callable with this signature works"; routing body:
```python
result: ModelResponse | Awaitable[ModelResponse]
if _utils.is_async_callable(self.function):
    result = self.function(messages, agent_info)
else:
    result = await _utils.run_in_executor(self.function, messages, agent_info)
response = await _utils.await_maybe(result)
assert isinstance(response, ModelResponse), response
```
**Data Shape:** `function`/`stream_function` accept plain functions, `async def` functions, or **callable-class instances** whose `__call__` is sync or async. Generated model name = `` f'function:{fn_name}:{stream_name}' `` where each component is `getattr(callable, '__name__', type(callable).__name__)`; explicit `model_name=` kwarg wins.

### Decisive source
```python
# function.py:128-135 — instance/partial names fall back to the CLASS name at construction time
function_name = (
    getattr(self.function, '__name__', type(self.function).__name__) if self.function is not None else ''
)
stream_function_name = (
    getattr(self.stream_function, '__name__', type(self.stream_function).__name__)
    if self.stream_function is not None
    else ''
)
self._model_name = model_name or f'function:{function_name}:{stream_function_name}'

# _utils.py:783-786 — partial-unwrapping async predicate (copied from Starlette)
while isinstance(obj, functools.partial):
    obj = obj.func
return inspect.iscoroutinefunction(obj) or (callable(obj) and inspect.iscoroutinefunction(obj.__call__))
```

**Flow:** Construction → per-callable `getattr('__name__', class-name fallback)` → generated name frozen at init. Request → `AgentInfo` built from `ModelRequestParameters` → `is_async_callable` unwraps nested `functools.partial` layers then accepts EITHER an `async def` object OR an object whose `__call__` is `async def` → true ⇒ called directly, returned coroutine awaited via `await_maybe`, ON the event loop; false ⇒ submitted to a worker thread (`run_in_executor`: ContextVar-chosen custom executor via `loop.run_in_executor(executor, ctx.run, guard)` else `anyio.to_thread.run_sync`, inline under `_disable_threads`), then `await_maybe` resolves what it RETURNED (a sync `__call__` may return a coroutine — still resolved). Usage estimation fills empty usage afterward.

**Invariant (routing):** `is_async_callable` is the ONLY gate between event-loop and thread. It unwraps `functools.partial` chains before inspecting, so a partial-wrapped async instance stays off the executor; a genuinely sync callable goes to the executor even though `await_maybe` would resolve a coroutine it returns. Output is IDENTICAL on both arms — only executor observability can distinguish routing, which is why the direct test pins it with a shut-down `ThreadPoolExecutor`.
**Invariant (naming):** the fallback fires at construction time only. A `functools.partial` has no `__name__` and no useful class name beyond `partial`, so `FunctionModel(functools.partial(hello_named, name='world'))` generates `function:partial:` — literal string `partial` as the component.
**Invariant (stream side):** `request_stream` (:212) wraps `self.stream_function(messages, agent_info)` in `PeekableAsyncStream` WITHOUT inspecting async-ness: the value RETURNED is the contract. An async-generator function or a sync `__call__` returning an async iterator works; an `async def __call__` that *returns* (not yields) an async iterator does NOT work — its coroutine is never awaited, so the peek yields Unset and raises `ValueError('Stream function must return at least one item')` (:214-216). The FunctionDef docstring (:313-319) writes this trap down verbatim.
**Probe:** `tests/models/test_model_function.py::test_init_callable_instance` (:174, three instance-shape names), `::test_async_callable_instance_does_not_need_a_worker_thread` (:187, shut-down executor pins routing: async + partial-wrapped instances run, sync instance raises `RuntimeError('cannot schedule new futures')`), `::test_sync_callable_instance_returning_coroutine` (:226, executor-arm coroutines still resolved), `::test_stream_callable_instance` (:234), `::test_stream_sync_callable_instance` (:248, sync stream `__call__` identical), `::test_partial_function` (:263, `function:partial:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "FunctionModel request callable instance", limit: 10, fields: ["signature", "name", "file"] });
// rank #1-3 line-exact: test_init_callable_instance :174 / test_sync_callable_instance :209 / test_stream_callable_instance :234
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "is_async_callable await_maybe", limit: 10, fields: ["signature", "name", "file"] });
// resolves _utils helpers incl. await_maybe docstring cross-reference
```

## Verdict
Adopt the two-axis dispatch: construction-time `getattr('__name__', class-name)` naming plus call-time partial-unwrapping `is_async_callable` routing with post-call `await_maybe` convergence — both are portable to any host that accepts user callables as stand-ins. Adapt the executor seam (`using_thread_executor` ContextVar vs your host's thread pool) to your runtime. Omit pydantic-ai's `AgentInfo` snapshot shape if your host already owns one. Caveat: direct tests executed green 25/25 at pin `fde1bbb6` in repo `.venv` (2026-08-24); coverage clean (`no_recorded_issue`) ×3 cited paths.
