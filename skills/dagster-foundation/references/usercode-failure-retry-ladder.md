<!-- capsule-v2 -->
# User-code-failure dequeue retry ladder — when a launch fails because the code server is down, what happens to the run?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does the queue distinguish "infrastructure hiccup, re-queue" from "run is broken, fail it", and how are retries counted without a retry counter column?

## PIPELINE_ENQUEUED event count IS the retry counter
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/run_coordinator/queued_run_coordinator_daemon.py:_dequeue_run` exception handler (lines 409-492); location timeout map `_location_timeouts` (:47-48, :429-434).
**Signature:** `def _dequeue_run(self, instance, workspace, run: DagsterRun, concurrency_config, fixed_iteration_time) -> bool` (True = launched).
**Data Shape:** Config knobs on `RunQueueConfig`: `max_user_failure_retries` (`max_user_code_failure_retries`) and `user_code_failure_retry_delay`. Retryable error classes: `DagsterUserCodeUnreachableError`, `DagsterCodeLocationLoadError`.

### Decisive source
```python
enqueue_event_records = instance.get_records_for_run(
    run_id=run.run_id, of_type=DagsterEventType.PIPELINE_ENQUEUED
).records

check.invariant(len(enqueue_event_records), "Could not find enqueue event for run")

num_retries_so_far = len(enqueue_event_records) - 1

if (
    num_retries_so_far
    >= concurrency_config.run_queue_config.max_user_code_failure_retries
):
    ...
    instance.report_run_failed(run)
    return False
else:
    ...
    # Re-submit the run into the queue
    enqueued_event = DagsterEvent.job_enqueue(run)
    instance.report_dagster_event(enqueued_event, run_id=run.run_id)
```
Plus the guard before any of this (:418-425): after a failure, re-fetch the run and if its status has already advanced past QUEUED/STARTING ("Make sure we don't re-enqueue a run if it has already finished or moved into STARTING") just move on — no re-enqueue of a run that actually started.

**Flow:** launch raises → capture serializable error → re-read status (race guard) → if user-code-unreachable class AND retries configured: set `self._location_timeouts[location_name] = now + retry_delay` under lock so ALL runs from that location pause dequeues for a cooldown ("to give its code server time to recover") → count prior PIPELINE_ENQUEUED events; N-1 = attempts used → below budget: emit engine error + fresh enqueue event (run returns to QUEUED, count grows by exactly one) → at budget: engine error + `report_run_failed`. Any other exception class ⇒ immediate unrecoverable failure ("Caught an unrecoverable error while dequeuing the run. Marking the run as failed and dropping it from the queue").
**Invariant:** Retry accounting is derived from the append-only event log — idempotent across daemon restarts, no schema change. Each retry writes exactly one ENQUEUED event, so `count-1` is monotonic. The location-level cooldown converts per-run failures into a backoff for the whole code location.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_queued_run_coordinator_daemon.py` — tests exercising `max_user_code_failure_retries` re-enqueue/fail behavior in `QueuedRunCoordinatorDaemonTests` (32 test functions in file).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_dequeue_run user code failure retries location timeouts", limit: 10 });
```

## Verdict
Adopt event-log-derived retry counting and the per-location cooldown keyed by error class; adapt the retryable-error class list to your launcher's failure taxonomy; omit gRPC-specific error strings. Coverage caveat: behavior pinned by upstream unit tests requiring dagster deps (blocked this window), source ranges verified byte-exact instead.
