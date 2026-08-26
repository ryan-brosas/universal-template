<!-- capsule-v2 -->
# Run-loop finally: futures + disconnect + tracking — What must always happen in the run-loop finally block, even on success?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** Which cleanups are unconditional (finally) versus success-only (wait_for_open_threads), and how are cancelled runs persisted through client disconnects?

## finally cancels side-effect futures and disconnects tools on EVERY exit
**Path/Symbol:** `libs/agno/agno/agent/_run.py:_run.finally` (:736-749); `_persist_cancelled_run_in_background` (:5927-5960).
**Signature:** finally block over `(memory_future, cultural_knowledge_future, learning_future)`; `_persist_cancelled_run_in_background(agent, run_response, session, run_context, user_id) -> None`.
**Data Shape:** futures from ThreadPoolExecutor (`future.cancel()` only works pre-run; `future.result(timeout=0)` reaps finished ones without blocking); module-level `_background_tasks: set` holds detached asyncio tasks.

### Decisive source
```python
finally:
    # Cancel background futures on error (wait_for_open_threads handles waiting on success)
    for future in (memory_future, cultural_knowledge_future, learning_future):
        if future is not None and not future.done():
            future.cancel()
            try:
                future.result(timeout=0)
            except Exception:
                pass
    # Always disconnect connectable tools
    disconnect_connectable_tools(agent)
    cleanup_run(run_response.run_id)

async def _persist() -> None:
    """On a client disconnect the request runs inside an anyio cancel scope;
    awaiting acleanup_and_store inline lets its DB write be re-cancelled
    mid-flight, losing the run."""
    await acleanup_and_store(...)
    if run_response.run_id:
        await acleanup_run(run_response.run_id)   # double-cleanup so the run is never left tracked
task = asyncio.create_task(_persist())
_background_tasks.add(task)
task.add_done_callback(_background_tasks.discard)
```

**Flow:** success path already JOINED the futures via wait_for_open_threads before returning normally — the finally sees done() futures and just reaps. Error/cancel paths reach finally with live futures which are cancelled. Disconnect path schedules the persistence OUTSIDE the anyio cancel scope so the DB write completes after the request dies.
**Invariant:** cancellation-tracking cleanup is deliberately DOUBLE (`_persist` calls acleanup_run even though `_arun`'s finally also does) because on disconnect that finally-await can itself be re-cancelled — a leaked registry entry would make the run_id unkillable/unrestartable. Connectable-tool disconnect must be unconditional or MCP-style sessions leak.
**Probe:** `grep -c 'disconnect_connectable_tools(agent)' libs/agno/agno/agent/_run.py` → **8** total call sites (sync/async/stream families' finally blocks + init pairing); `grep -c 'asyncio.create_task(_persist())' libs/agno/agno/agent/_run.py` → **1**; direct behavior test `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_cancel_agent_during_async_streaming`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_persist_cancelled_run_in_background disconnect_connectable_tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the unconditional-finally discipline and detached-persist-on-disconnect pattern; adapt the future trio to your side-effect workers; omit anyio specifics if your stack differs but keep write-outside-the-dying-scope semantics.
