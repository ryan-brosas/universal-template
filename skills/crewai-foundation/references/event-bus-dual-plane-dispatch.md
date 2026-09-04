<!-- capsule-v2 -->
# Event bus dual-plane dispatch — how do sync and async handlers coexist on one singleton bus without blocking the loop or leaking futures?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What threading model lets `emit()` be called from any thread while async handlers run on a dedicated loop?

## ThreadPool for sync, run_coroutine_threadsafe for async
**Path/Symbol:** `lib/crewai/src/crewai/events/event_bus.py` (`emit` :572–647, `_call_handlers` :401–426, `_acall_handlers` :429–444, `_track_future` :193–211, `flush` :734–769, `shutdown` :897–950 + atexit :952).
**Signature:** `emit(self, source: Any, event: BaseEvent) -> Future[None] | None`.
**Data Shape:** handler sets are FROZENSETS snapshotted under read lock; `_pending_futures: set[Future]` with per-future discard callback.

### Decisive source
```python
if sync_handlers:
    if event_type is LLMStreamChunkEvent:
        self._call_handlers(source, event, sync_handlers, state)
    else:
        ctx = contextvars.copy_context()
        sync_future = self._sync_executor.submit(
            ctx.run, self._call_handlers, source, event, sync_handlers, state
        )
        if not async_handlers:
            return self._track_future(sync_future)

if async_handlers:
    return self._track_future(
        asyncio.run_coroutine_threadsafe(
            self._acall_handlers(source, event, async_handlers, state),
            self._loop,
        )
    )
```
```python
async def _acall_handlers(self, source, event, handlers, state):
    coros = [_call(handler) for handler in handlers]
    results = await asyncio.gather(*coros, return_exceptions=True)
```

**Flow:** read-lock snapshot of handler sets + shutdown flag → no handlers ⇒ None → stream-chunk events run sync INLINE (ordering-critical); everything else submits to the thread executor WITH copied contextvars → async handlers hop to the bus's daemon-loop via `run_coroutine_threadsafe` → returned future is tracked so `flush()` can wait; handler exceptions never raise into the emitter (printed per-handler).
**Invariant:** Handler snapshots under the RWLock mean registration during dispatch affects only LATER events. The 3-arg handler protocol `(source, event, state)` is detected by param count. Shutdown flips the flag under write-lock first: emits during teardown warn-and-drop instead of racing the dying loop; atexit guarantees the daemon loop joins.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/utilities/events/test_thread_safety.py" "lib/crewai/tests/utilities/events/test_shutdown.py" -q` (expect 18 passed incl. concurrent emit/register and handlers-complete-before-shutdown-flag).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "event bus emit sync executor run_coroutine_threadsafe flush track future", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-under-lock + dual-plane dispatch + tracked futures; adapt the inline stream-chunk carve-out to your ordering needs; omit runtime-state passing if handlers need no entity snapshot.
