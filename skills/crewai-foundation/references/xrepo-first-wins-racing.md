<!-- capsule-v2 -->
# Cross-repo pattern: first-wins racing over asyncio — crewAI's racing OR-listeners vs langgraph's FIRST_COMPLETED drain

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`_execute_racing_listeners` :1147–1196); cross-ref graph `ext-langgraph` `libs/langgraph/langgraph/pregel/_runner.py` :280–310 (sync) / :480–510 (async). Codebase Memory projects `ext-crewAI`, `ext-langgraph`. **Question:** What do two independent agent-framework engines agree on when many coroutines race and only the first result matters?

## Pattern: iterate completions, take the first success, cancel the rest
**Path/Symbol:** crewAI `flow/runtime/__init__.py:1183–1193`; langgraph `pregel/_runner.py` (`pacer`/wait loop with `return_when=FIRST_COMPLETED`).
**Signature:** crewAI: `async def _execute_racing_listeners(racing_listeners, other_listeners, result, triggering_event_id=None)`; langgraph: `while len(futures) > ...: done, inflight = await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED, timeout=...)`.
**Data Shape:** crewAI groups members as `frozenset[FlowMethodName] → or_listener`; langgraph keeps a `dict[Future, Task|None]` where None marks waiter slots.

### Decisive source
```python
# crewAI — first SUCCESS wins; failures are skipped, not terminal
for coro in asyncio.as_completed(racing_tasks):
    try:
        await coro
    except Exception as e:
        logger.debug(f"Racing listener failed: {e}")
        continue
    break

for task in racing_tasks:
    if not task.done():
        task.cancel()
```
```python
# langgraph — same skeleton, batch-drain variant
done, inflight = await asyncio.wait(
    futures,
    return_when=asyncio.FIRST_COMPLETED,
    timeout=(max(0, end_time - loop.time()) if end_time else None),
)
if not done:
    break  # timed out
```

**Flow:** both engines launch all racing tasks eagerly → consume completion events one at a time → the FIRST usable completion ends the race → unfinished siblings are cancelled/abandoned → non-racing work in the same wave proceeds independently (crewAI gathers `other_tasks` with return_exceptions; langgraph keeps its waiter slot).
**Invariant:** Shared semantics both engines encode: exceptions do NOT win races — a failing racer must be skipped so a later success can still claim victory (crewAI's continue-on-exception; langgraph routes task exceptions to error handlers instead of treating them as done-winners). Cancellation is best-effort cleanup AFTER the winner exists, never part of selection. Timeouts bound the whole race, not per-task.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_or_listener_fires_once_across_parallel_starts" -q` (expect 1 passed); static anchors: crewAI `as_completed` ×1 :1183; langgraph `return_when=asyncio.FIRST_COMPLETED` :484.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "racing listeners first-wins as_completed cancel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared contract (first-success-wins, cancel-after-victory, bounded race) for any alternative-sourcing problem; adapt grouping keys to your domain; omit failure-skipping only when any failure should abort the race.
