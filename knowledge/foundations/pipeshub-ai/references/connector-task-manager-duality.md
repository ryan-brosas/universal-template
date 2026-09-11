<!-- capsule-v2 -->
# Keyed background-task manager — cancel-and-restart vs decline-if-busy: which start semantics belong to syncs vs reindex?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** A platform needs "one task per connector id" for two different jobs with OPPOSITE duplicate policies — where is that line drawn?

## SyncTaskManager dual verbs over strong-ref task table
**Path/Symbol:** `backend/python/app/connectors/core/sync/task_manager.py:` (whole, 195L) — `start_sync` (:cancel+await+spawn), `start_if_idle` (:check+close-coroutine+decline), `_spawn`, `cancel_sync`, `cancel_all`.
**Signature:** `async def start_sync(key, coro) -> asyncio.Task` (restarts); `async def start_if_idle(key, coro) -> Optional[asyncio.Task]` (returns None when busy); `_spawn` wraps coro in `_traced()` that inherits request context or mints `new_system_root()`.
**Data Shape:** `_tasks: Dict[str, asyncio.Task]` STRONG references ("the event loop keeps only weak ones, so an unreferenced task can be collected mid-flight"); done-callback auto-removes.

### Decisive source
```python
if self.is_running(key):
    # The caller already built the coroutine; closing it avoids
    # "coroutine was never awaited".
    coro.close()
    return None        # reindex: redelivered Kafka event must NOT restart progress
```
vs `start_sync`: manual re-sync CANCELS the in-flight run first (`await self.cancel_sync(key)`) then spawns fresh.

**Flow:** choose verb by semantics: user-triggered sync ⇒ replace (fresh state wins); machine-redelivered reindex ⇒ decline (progress monotonic). Spawn names tasks `{label}_{key}` for diagnostics; context inheritance means triggered syncs keep their request's trace while pure background triggers get a system root (telemetry continuity).
**Invariant:** The no-await-between-check-and-spawn comment pins event-loop atomicity for `start_if_idle`. Declining MUST `coro.close()` — Python raises "coroutine was never awaited" warnings otherwise, and the caller-built coroutine leaks. Never let both verbs share one policy: restart-on-duplicate would rewind reindex progress on every Kafka redelivery.
**Probe:** `grep -c 'async def start_if_idle' app/connectors/core/sync/task_manager.py` → `1`; suite `tests/unit/connectors/core/test_sync_task_manager.py` (17 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "SyncTaskManager start_if_idle start_sync", limit: 3 });
```
**Verdict:** Adopt the two-verb split as-is; adapt labels/context plumbing. Directly reusable for ANY keyed-job runner (crawl managers, worker pools).
