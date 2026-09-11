<!-- capsule-v2 -->
# Ticker scheduler gate ladder — in what order must due-ness, schedule windows, and backpressure be evaluated?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** What checks does the 1-second scheduler loop run per watch before enqueueing, and which failures are skip-vs-abort?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/flask_app.py:ticker_thread_check_time_launch_checks` (:1203-1366); thread spawn :1095 (`TickerThread-ScheduleChecker`, daemon); `MAX_QUEUE_SIZE = 5000` (:61).
**Signature:** `def ticker_thread_check_time_launch_checks() -> None` — infinite `while not app.config.exit.is_set():` loop, `app.config.exit.wait(1.0)` between iterations (0.01s under pytest).
**Data Shape:** Reads per-watch dict fields (`paused`, `time_between_check_use_default`, `time_schedule_limit`, `last_checked`, `jitter_seconds`) and global settings (`all_paused`, jitter, workers). Local `proxy_last_called_time` memo persists across iterations.

### Decisive source
```python
if datastore.data['settings']['application'].get('all_paused', False):
    app.config.exit.wait(1)
    continue
...
seconds_since_last_recheck = now - watch['last_checked']
if seconds_since_last_recheck >= (threshold + watch.jitter_seconds) and seconds_since_last_recheck >= recheck_time_minimum_seconds:
    if not uuid in running_uuids and uuid not in queued_uuids:
        ...
        priority = int(time.time())
        queued_successfully = worker_pool.queue_item_async_safe(update_q, PrioritizedItem(priority=priority, item={'uuid': uuid}))
```
```python
# Re #438 - Check queue size every 100 watches for CPU efficiency (not every watch)
if watch_index % 100 == 0:
    current_queue_size = update_q.qsize()
    if current_queue_size >= MAX_QUEUE_SIZE:
        break   # stops THIS scheduling iteration only
```

**Flow:** per iteration: (1) every 60s run `worker_pool.check_worker_health()` self-repair; (2) global pause short-circuits the whole tick; (3) snapshot watch list sorted by `last_checked` ascending (most over-due first) with a retry-on-RuntimeError deepcopy guard (issue #232: dict mutates mid-iteration); (4) per watch ladder: paused → skip; time-schedule window (watch-level if set else global) → skip when outside; threshold+jitter due check → fall through; already running/queued → skip; proxy reuse-time minimum → skip this watch but record use when eligible; then enqueue at epoch priority. Queue-size backpressure sampled every 100 watches aborts the sweep, never individual watches.
**Invariant:** Due-ness is `>= threshold + jitter` AND `>= MINIMUM_SECONDS_RECHECK_TIME` (floor 3s env-tunable) — a tiny per-watch threshold can never hot-loop because of the system floor. Jitter is drawn ONCE per cycle (`uniform(-abs(j), j)`) and reset to 0 after successful enqueue.
**Probe:** `grep -c 'all_paused' changedetectionio/flask_app.py` → `1` (:1237 — single global-pause gate); `grep -cF 'MAX_QUEUE_SIZE' changedetectionio/flask_app.py` → `3`; `grep -c 'watch_index % 100' changedetectionio/flask_app.py` → `1`.
**Direct test:** `changedetectionio/tests/test_scheduler.py:test_check_basic_scheduler_functionality` — with all days disabled and `time_schedule_limit-enabled='y'`, `last_checked` must NOT advance; enabling today's day in Pacific/Kiritimati (+14h tz chosen to surface day-boundary bugs) lets it advance.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "ticker_thread_check_time_launch_checks", limit: 3 });
// → ext-changedetection.io.changedetectionio.flask_app.ticker_thread_check_time_launch_checks Function flask_app.py 1203-1366
```

## Verdict
Adopt the ordered gate ladder + most-overdue-first sort + periodic health repair as a scheduler skeleton. Adapt the pause flag and thresholds to your config schema. Omit the proxy-reuse memo if you have no shared egress resources.
