<!-- capsule-v2 -->
# MCP per-group episode queue — sequential ingestion without blocking callers

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** how does a server accept episodes concurrently but process each group's episodes strictly in order, and what happens when a worker dies mid-loop?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/services/queue_service.py`: `QueueService` (:12), `add_episode_task` (:24), `_process_episode_queue` (:49), `add_episode` (:101).
**Signature:** `add_episode_task(group_id: str, process_func: Callable[[], Awaitable[None]]) -> int`; internal `async def _process_episode_queue(group_id) -> None` runs `while True: func = await queue.get(); await func()` with `task_done()` in `finally`.
**Data Shape:** three dicts keyed by group_id — `_episode_queues: dict[str, asyncio.Queue]`, `_queue_workers: dict[str, bool]`, plus one injected `_graphiti_client`. The queued item is a zero-arg async closure capturing all add_episode kwargs. Return value is the queue position (`qsize()`), not a result handle.

### Decisive source
```python
if not self._queue_workers.get(group_id, False):
    asyncio.create_task(self._process_episode_queue(group_id))
return self._episode_queues[group_id].qsize()
...
while True:
    process_func = await self._episode_queues[group_id].get()
    try:
        await process_func()
    except Exception as e:
        logger.error(...)          # swallow per-item errors
    finally:
        self._episode_queues[group_id].task_done()
except asyncio.CancelledError:
    ...
finally:
    self._queue_workers[group_id] = False   # flag cleared even on cancel/crash
```

**Flow:** caller → closure built around `graphiti_client.add_episode` (reference_time defaulted to `datetime.now(timezone.utc)` at execution time, not enqueue time) → put on that group_id's queue → lazy worker spawn if no `_queue_workers[group_id]` flag → worker drains serially forever (never exits on empty queue; blocks on `get()`).
**Invariant:** two properties a porter gets wrong: (1) per-item exceptions are swallowed so one poisoned episode cannot kill the group's ordering guarantee — only `CancelledError` or an exception outside the loop ends the worker; (2) if the worker task is cancelled while items remain queued, the flag resets to False, so the NEXT enqueue re-spawns a fresh worker from the surviving queue — recovery is implicit in the flag+queue pair, not in any explicit supervisor.
**Probe:** `mcp_server/tests/test_core_parity.py::TestQueueServiceThreading::test_add_episode_forwards_all_params` + `test_add_episode_defaults_reference_time_to_now` (all kwargs forwarded verbatim; reference_time defaults to *now*).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "QueueService add_episode_task _process_episode_queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dict-of-queues keyed by partition key + lazy single-worker-per-key pattern for ordered background ingestion (works for any serialize-by-key workload). Adapt the closure shape to your host's job payload; omit the fire-and-forget `create_task` without a keep-reference set (a porter should store the task handle to avoid GC). Caveat: direct tests pin param forwarding/defaulting, not cancellation recovery.
