<!-- capsule-v2 -->
# Spawn futures registry — how do you track fire-and-forget child tasks per conversation thread so a stream can end without orphaning tool-inheriting children?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** What is the process-wide bookkeeping that lets a parent agent spawn async sub-agents, poll/cancel their futures, and guarantee cleanup when the parent stream stops or resets?

## Three process-wide maps keyed by thread-or-"_default"
**Path/Symbol:** `src/cuga/backend/agent_spawn/runtime.py` — `_futures_by_thread` / `_tasks_by_thread` / `_task_by_future` (46–48), `thread_spawn_futures` 69–72, `pop_spawn_future` 75–80, `cancel_spawn_future` 83–94, `clear_runtime_caches` 97–114, `wait_pending_spawns` 122–142, `_track_task` 145–159; consumers `server/main.py:stop` + `:reset_agent_state`; direct tests `tests/unit/test_agent_spawn.py`.
**Signature:** `_track_task(thread_id, future_id, task)` registers into all three maps; `clear_runtime_caches(thread_id: Optional[str])` — None cancels ALL tasks then clears every map, a thread key cancels that thread's tasks, pops its future_ids from the global map, drops both buckets.
**Data Shape:** future rows are `{"status": "running|done|cancelled|error|timeout", "result": str|None, "error": str|None}`; task buckets are `Set[asyncio.Task]`.

### Decisive source
```python
# runtime.py:151-157 — IDENTITY-guarded bucket eviction (the load-bearing subtlety)
def _done(t: asyncio.Task) -> None:
    bucket.discard(t)
    _task_by_future.pop(future_id, None)
    # Only pop if this callback's bucket is still the live map entry — a
    # reused thread_id may have a fresher bucket after clear_runtime_caches.
    if not bucket and _tasks_by_thread.get(key) is bucket:
        _tasks_by_thread.pop(key, None)
```
```python
# runtime.py:130-142 — bounded drain with cancel-on-timeout so streams end clean
pending = pending_spawn_tasks(thread_id)
if not pending: return
try:
    await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)
except asyncio.TimeoutError:
    ...
    if cancel_on_timeout and still:
        clear_runtime_caches(thread_id)
```

**Flow:** `execute_async` mints `future_<hex>`, seeds the future row `running`, `asyncio.create_task`s `_execute_and_store`, then `_track_task(parent_thread_id, future_id, …)`. Done callbacks discard the task, pop the future→task mapping, and evict empty buckets ONLY on identity match. `/stop` sets the stop event + `clear_runtime_caches(thread_id)`; `/reset` clears the stop event + caches + citation ledger (`drop_ledger`) — both warn-not-raise around cache clearing. `wait_pending_spawns` drains children before a parent stream ends (`timeout=5.0`, `cancel_on_timeout=True` defaults, signature-pinned by test). Contextvars isolate spawn depth and the per-stream emit callback across concurrent AgentLoop streams.
**Invariant:** bucket eviction must be identity-guarded because done-callbacks fire LATE: after `clear_runtime_caches(key)` replaced the bucket, an old task's callback would otherwise pop the fresh bucket off the map, losing live tasks. Direct-tested by `tests/unit/test_agent_spawn.py:688 test_track_task_done_does_not_evict_fresh_bucket`.
**Probe:** upstream suite executed this pass — `.venv/bin/python -m pytest tests/unit/test_agent_spawn.py::test_track_task_done_does_not_evict_fresh_bucket tests/unit/test_agent_spawn.py::test_wait_pending_spawns_cancels_on_timeout tests/unit/test_agent_spawn.py::test_wait_pending_spawns_default_timeout_is_five_seconds --confcutdir=tests/unit -q` → **3 passed**.
**Executed:** observed `3 passed in 4.08s` (runner: `PYTHONPATH=src .venv/bin/python -m pytest … --confcutdir=tests/unit` from repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "clear_runtime_caches track_task wait_pending_spawns futures", limit: 10 });
```
(Executed pre-write; `trace_path` inbound on `clear_runtime_caches` resolves exactly four callers: `wait_pending_spawns`, `AgentLoop.run_stream`, `main.stop`, `main.reset_agent_state`.)

## Verdict
Adopt the three-map layout with identity-guarded eviction, thread-scoped vs global clear duality, and the drain-with-cancel-on-timeout contract for ending parent streams. Adapt the 5s default and the future-row status vocabulary to your host. Omit the `_default` sentinel only if your threads are always non-empty strings — but keep SOME fallback key or unparented spawns become untracked.
