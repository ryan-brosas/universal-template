<!-- capsule-v2 -->
# Constellation cancellation ladder — How do you cancel one running DAG cleanly when the executor handles many?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** What is the correct ordering of flags, future cancellation, and reaping so a cancelled constellation stops promptly, skips finished work, and leaves no zombie tasks?

## Dual flag → cancel not-done futures → gather exceptions
**Path/Symbol:** `galaxy/constellation/orchestrator/orchestrator.py:TaskConstellationOrchestrator.cancel_execution` (:99-141).
**Signature:** `async def cancel_execution(self, constellation_id: str) -> bool`.
**Data Shape:** `_cancellation_requested: bool` (global stop), `_cancelled_constellations: Dict[str, bool]` (per-DAG stop), `_execution_tasks: Dict[task_id, asyncio.Task]`.

### Decisive source
```python
self._cancellation_requested = True
self._cancelled_constellations[constellation_id] = True

if self._execution_tasks:
    for task_id, task in list(self._execution_tasks.items()):
        if not task.done():
            task.cancel()
    # Wait for all cancellations to complete
    await asyncio.gather(*self._execution_tasks.values(),
                         return_exceptions=True)
    self._execution_tasks.clear()
```
and in the run loop (:401-410):
```python
if self._cancellation_requested or self._cancelled_constellations.get(
        constellation.constellation_id, False):
    constellation.state = ConstellationState.CANCELLED
    break
```

**Flow:** set both flags first (so the loop's next iteration sees them even if future cancellation races) → iterate a *copy* of the registry, cancelling only futures not yet done → `gather(..., return_exceptions=True)` reaps CancelledError without propagating → clear the map; the loop converts its own observation of the flag into `ConstellationState.CANCELLED` and breaks.
**Invariant:** done futures are never `.cancel()`ed again; cancellation is idempotent — calling it twice must be safe; the caller waits until every future has actually settled before clearing state.
**Probe:** `tests/galaxy/constellation/test_orchestrator_cancellation.py:57-117` pins flag setting (`_cancellation_requested`, per-constellation entry), that both running mocks get exactly one `cancel()`, and that the done mock's `cancel` is **not** called; :244-259 pins idempotence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "cancel execution cancelled constellations running tasks", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the ordering: flags before cancels, skip-done filter, exception-swallowing gather, map clear only after settling. Adapt the dual-scope flags to your naming (global vs per-entity) and add timeout on the reap gather if your tasks can ignore cancellation. Omit UFO's logging and the CANCELLED-state write if your DAG object has different terminal-state plumbing.
