<!-- capsule-v2 -->
# Health-check self-repair + brutal cancel-with-replacement — who revives dead workers, and how is one stuck job cancelled?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** How does the system detect and replace dead workers, and what is the contract for cancelling a single running watch?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker_pool.py:check_worker_health` (:568-622), `cancel_running_uuid` (:244-282); caller `flask_app.py` ticker :1219-1234.
**Signature:** `check_worker_health(expected_count, update_q=None, notification_q=None, app=None, datastore=None) -> dict(status='healthy'|'repaired'|'degraded', ...)`.
**Data Shape:** Health dict carries expected_count/actual_count/dead_workers/restarted_workers; cancel result `{cancelled: bool, worker_id: int|None, replaced: bool}`.

### Decisive source
```python
alive_count = sum(1 for w in worker_threads if w.thread and w.thread.is_alive())
if alive_count == expected_count:
    return {'status': 'healthy', ...}
# Find dead workers ... remove from tracking (reversed index pop)
missing_workers = expected_count - alive_count
if missing_workers > 0 and all([update_q, notification_q, app, datastore]):
    for i in range(missing_workers):
        if add_worker(update_q, notification_q, app, datastore):
            restarted_count += 1
return {'status': 'repaired' if restarted_count > 0 else 'degraded', ...}
```
```python
# cancel_running_uuid: drop tracking FIRST (under lock), then stop the thread,
# then spawn a replacement so concurrency stays at the configured level.
with _uuid_processing_lock:
    worker_id = currently_processing_uuids.get(uuid)
    currently_processing_uuids.pop(uuid, None)
    _uuid_started_at.pop(uuid, None)
...
target.stop()                       # loop.call_soon_threadsafe(loop.stop) — no join
worker_threads.remove(target)
replaced = bool(add_worker(update_q, notification_q, app, datastore))
```

**Flow:** Ticker calls health check every 60s with `expected_count = FETCH_WORKERS env or settings.workers`. Dead threads are pruned by reversed-index pops (index stability), missing workers re-added via `add_worker`, which also runs `_ensure_queue_executor()` first. Cancel path never waits on the dying worker — it unclaims the UUID synchronously so the UI immediately shows idle, kills the loop, and restores fleet size with a fresh worker (fresh loop, no poisoned state).
**Invariant:** Fleet-size reconciliation is count-based against expected, not identity-based — a half-dead registry heals to exactly expected_count. Cancellation of an unclaimed UUID returns `{'cancelled': False, 'worker_id': None, 'replaced': False}` without side effects.
**Probe:** `grep -c "w.thread.is_alive()" changedetectionio/worker_pool.py` → `2`; `grep -c "'repaired' if restarted_count > 0 else 'degraded'" changedetectionio/worker_pool.py` → `1`; `grep -c 'def cancel_running_uuid' changedetectionio/worker_pool.py` → `1`.
**Direct test:** `tests/test_queue_ui.py:test_cancel_running_uuid_helper` — claims synthetic uuid, asserts started_at present, cancels, asserts `get_uuid_started_at(...) is None` and second cancel of unknown uuid returns falsy cancelled.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "check_worker_health restart crashed async workers", limit: 5 });
// → ext-changedetection.io.changedetectionio.worker_pool.check_worker_health Function worker_pool.py 568-622
```

## Verdict
Adopt periodic expected-vs-alive reconciliation as the watchdog pattern for daemon fleets. Adapt the expected-count source. Omit graceful drain if your shutdown model is process-exit (document it like upstream's "brutal" comments).
