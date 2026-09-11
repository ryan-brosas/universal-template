<!-- capsule-v2 -->
# Per-worker event loop + restartable coroutine shell — how do 200 fetch workers scale without thread exhaustion?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** What is the lifecycle contract of a worker (thread → loop → coroutine) and when does it self-restart vs exit?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker_pool.py:WorkerThread` (:40-109), `start_single_async_worker` (:134-169), `_ensure_queue_executor` (:177-187); restart policy in `worker.py:async_update_worker` (:66-76, :748-759).
**Signature:** `WorkerThread(worker_id, update_q, notification_q, app, datastore)`; `start_single_async_worker(...) -> None` loops `async_update_worker(...) -> "restart" | "shutdown"`.
**Data Shape:** Env knobs read at worker start: `WORKER_MAX_JOBS` (default 10), `WORKER_MAX_RUNTIME` (default 3600s), `FETCH_WORKERS` (sizes BOTH the worker fleet and the shared `QueueGetter-` ThreadPoolExecutor). Each `WorkerThread` owns `asyncio.new_event_loop()`; threads are daemons named `PageFetchAsyncUpdateWorker-<id>`.

### Decisive source
```python
while not app.config.exit.is_set():
    try:
        result = await async_update_worker(worker_id, update_q, notification_q, app, datastore, executor)
        if result == "restart":
            continue          # immediately loop back and restart
        else:
            break             # clean shutdown
    except asyncio.CancelledError:
        break
    except Exception as e:
        logger.error(f"Async worker {worker_id} crashed: {e}")
        await asyncio.sleep(5)   # crash backoff, then restart
```
```python
# _ensure_queue_executor: after a brutal shutdown_workers(), the executor stays
# poisoned ('cannot schedule new futures after shutdown') — recreate before reuse.
if queue_executor is None or getattr(queue_executor, '_shutdown', False):
    queue_executor = ThreadPoolExecutor(max_workers=_max_executor_workers,
                                        thread_name_prefix="QueueGetter-")
```

**Flow:** app init starts FETCH_WORKERS WorkerThreads (:1089 flask_app). Each creates its own loop and runs the shell. The inner worker returns `"restart"` after max_jobs processed OR max_runtime elapsed — checked ONLY at safe points: idle-timeout branch (:102-107) and end-of-job finally (:752-759) — never mid-job. Crash inside a job does NOT bubble out: per-job exception handlers record last_error on the watch; only an unhandled escape reaches the shell's 5s-backoff restart.
**Invariant:** Executor must be sized ≥ worker count because EVERY blocking queue get runs in it (`run_in_executor`), one thread per waiting worker; `_ensure_queue_executor` must run before ANY add_worker/start path or restarted workers insta-die. Stop is brutal by design (`loop.call_soon_threadsafe(loop.stop)`, no join) — daemons die with the process; health is reconciled by the ticker's periodic check instead of graceful joins.
**Probe:** `grep -c 'return "restart"' changedetectionio/worker.py` → `2` (idle :107 + post-job :759); `grep -c '_ensure_queue_executor' changedetectionio/worker_pool.py` → `3`; `grep -c 'cannot schedule new futures after shutdown' changedetectionio/worker_pool.py` → `2` (:181 docstring + :430 comment); `grep -c 'cannot schedule new futures after shutdown' changedetectionio/worker.py` → `1`.
**Direct test:** `tests/test_queue_handler.py:test_queue_system` scales workers via `client.application.set_workers(items)` then asserts parallel completion timing; `test_queue_ui.py:test_cancel_running_uuid_helper` pins replacement-worker semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "start_single_async_worker restart", limit: 5 });
// CLI: search_graph '{"project":"ext-changedetection.io","query":"async_update_worker","limit":5,"detail":"ids"}'
```

## Verdict
Adopt thread-per-loop isolation plus sentinel-returning coroutine shells for mixed sync/async fleets. Adapt env knob names/defaults. Omit pytest-log softening branches (cosmetic).
