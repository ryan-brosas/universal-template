<!-- capsule-v2 -->
# Cross-repo pattern: copy-context thread hop — crewAI's sync-method shim vs agno's parallel-fanout deepcopy guard

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`_execute_method` :2884–2890); cross-ref fleet precedent agno `parallel-fanout-backpressure` deepcopy-per-branch + cancel-pierces-gather ([DONE:330]). Codebase Memory projects `ext-crewAI`, `ext-agno`. **Question:** What do agent frameworks do at the async/sync boundary to keep per-execution context from leaking or vanishing?

## Pattern: snapshot context (or state) BEFORE crossing, never share the live object
**Path/Symbol:** crewAI `ctx = contextvars.copy_context(); await asyncio.to_thread(ctx.run, method, ...)`; ask() timeout arm repeats it (`:3453–3456`). agno deep-copies branch state before parallel fan-out for the same reason.
**Signature:** `_execute_method(...)` sync arm; identical shape in `Flow.ask` provider submission.
**Data Shape:** copied ContextVars: `current_flow_id/name/method_name`, OTel baggage (`flow_inputs`, `flow_input_files`), tracing flags.

### Decisive source
```python
if asyncio.iscoroutinefunction(method):
    result = await method(*args, **kwargs)
else:
    # Run sync methods in thread pool for isolation
    # This allows Agent.kickoff() to work synchronously inside Flow methods
    ctx = contextvars.copy_context()
    result = await asyncio.to_thread(ctx.run, method, *args, **kwargs)
```
```python
# same discipline at the input-provider boundary (ask())
executor = ThreadPoolExecutor(max_workers=1)
ctx = contextvars.copy_context()
future = executor.submit(
    ctx.run, provider.request_input, message, cast(Any, self), metadata
)
```

**Flow:** every hop from loop-thread to worker-thread first snapshots the context → worker runs against the frozen view (set-in-worker mutations stay local) → results return by value; the engine then auto-awaits any coroutine a sync method produced.
**Invariant:** The snapshot must happen on the LOOP side before submission — copying inside the worker captures the wrong (empty) context. This is the same invariant agno encodes with per-branch deepcopy: concurrent branches/workers may READ shared state but must not alias it while it mutates. Ports that skip the copy lose flow-id attribution in events, telemetry baggage, and memory scoping nondeterministically under load.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_mixed_sync_async_execution_order" "lib/crewai/tests/test_flow_ask.py::TestAskTimeout::test_ask_timeout_returns_none" -q` (expect 2 passed exercising both hops).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "to_thread copy_context sync method isolation context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-before-hop as a hard rule at every async/sync seam; adapt payload copying depth to your mutation graph; omit auto-await only if your callers never mix styles.
