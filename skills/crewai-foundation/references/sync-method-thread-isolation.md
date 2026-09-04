<!-- capsule-v2 -->
# Sync-method thread-pool isolation — how does a sync flow method run inside an async engine without blocking the loop, and what context must ride along?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I execute user-supplied sync callables under asyncio so nested sync agent code and ContextVars behave?

## copy_context + to_thread + auto-await
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._execute_method` :2812–2987; hook param round-trip :2846–2859).
**Signature:** `_execute_method(self, method_name: FlowMethodName, method: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, str | None]`.
**Data Shape:** returns `(result, finished_event_id)` where event id is `None` when events are suppressed.

### Decisive source
```python
if asyncio.iscoroutinefunction(method):
    result = await method(*args, **kwargs)
else:
    # Run sync methods in thread pool for isolation
    # This allows Agent.kickoff() to work synchronously inside Flow methods
    ctx = contextvars.copy_context()
    result = await asyncio.to_thread(ctx.run, method, *args, **kwargs)
finally:
    current_flow_method_name.reset(method_name_token)

# Auto-await coroutines returned from sync methods (enables AgentExecutor pattern)
if asyncio.iscoroutine(result):
    result = await result
```

**Flow:** PRE_STEP hook may rewrite params (positional args live under `_0,_1,...` keys and are re-sorted back) → method-name ContextVar set BEFORE copy_context so the value propagates into the worker thread → async method awaited inline; sync method run via `asyncio.to_thread(ctx.run, ...)` → a sync method RETURNING a coroutine is awaited automatically → POST_STEP hook may replace output before bookkeeping.
**Invariant:** `contextvars.copy_context()` is mandatory: without it, `current_flow_id`/`current_flow_method_name`/baggage set on the loop do not reach the thread. The method-name token is reset in `finally` even when the callable raises. Hook param re-materialization sorts `_N` keys numerically — dropping that step silently converts positional args into kwargs.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_mixed_sync_async_execution_order" "lib/crewai/tests/test_flow.py::test_flow_with_exceptions" -q` (expect 2 passed; pins sync/async interleaving order and failure propagation through the wrapper).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_execute_method sync thread pool to_thread copy_context coroutine", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-context-then-to_thread plus returned-coroutine auto-await as the universal sync-call shim; adapt the hook parameter round-trip if you have no interception layer; omit CrewAI-specific event emission. Direct tests executed green at pin.
