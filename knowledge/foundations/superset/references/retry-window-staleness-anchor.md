<!-- capsule-v2 -->
# retry-window-staleness-anchor — How do retries survive across celery requeues yet yield to a new crontab window?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** When a failing schedule retries via re-enqueued tasks, how does the system know a retry belongs to the *same* crontab trigger — and detect that a *new* window has fired?

## Crontab-window identity anchor
**Path/Symbol:** `superset/commands/report/execute.py` — `_normalize_dttm` (:1508-1516), `_is_retry_window_stale` (:1518-1530), `_increment_retry` (:1532-1539), `_reset_retry_counter` (:1541-1544), `_schedule_retry` (:1546-1557); consumer at `ReportNotTriggeredErrorState.next` :1731-1754.
**Signature:** `_is_retry_window_stale(self) -> bool`; `_schedule_retry(self, delay_seconds: int) -> None`.
**Data Shape:** `report_schedule.retry_attempt: int`, `retry_scheduled_dttm: DateTime` (naive DB column, no tz), `_scheduled_dttm: datetime` (may be tz-aware depending on broker).

### Decisive source
```python
@staticmethod
def _normalize_dttm(dt):
    """Strip timezone info and microseconds so naive/aware datetimes can
    be compared safely. MySQL DateTime columns truncate microseconds,
    so without this the round-tripped anchor would differ from the
    in-memory value."""
    if dt is not None:
        return dt.replace(tzinfo=None, microsecond=0)
    return dt

def _is_retry_window_stale(self) -> bool:
    anchor = self._normalize_dttm(self._report_schedule.retry_scheduled_dttm)
    current = self._normalize_dttm(self._scheduled_dttm)
    return anchor is not None and anchor != current

def _schedule_retry(self, delay_seconds: int) -> None:
    from superset.tasks.scheduler import execute as execute_task  # lazy: circular dep
    # Pass the original crontab-trigger timestamp so the retry task
    # shares the same window identity.
    execute_task.apply_async(
        (self._report_schedule.id, self._scheduled_dttm.isoformat()),
        countdown=delay_seconds,
    )
```

**Flow:** first failure → `_handle_retry_or_error` resets the counter if the stored anchor differs from this tick's `scheduled_dttm` (fresh budget per window) → each retry re-enqueues the execute task carrying the **original** trigger timestamp, so all attempts of one window share one identity → next tick compares its own scheduled time against the persisted anchor: equal ⇒ same window, proceed with retry state; different while `last_state == RETRYING` ⇒ a new window fired mid-retries → skip entirely **unless** the chain looks dead (`last_eval_dttm` older than `ALERT_REPORTS_RETRY_MAX_DELAY_SECONDS`, e.g. `apply_async` failed after committing RETRYING) → then let the new window run. Equality requires normalization: DB stores naive µs-truncated datetimes; brokers may deliver tz-aware ones — comparing raw values would falsely mark every retry stale (or crash).
**Invariant:** Retry budget is per-crontab-window, never global; a persisted anchor must be compared only after naive/microsecond normalization; an in-flight healthy retry chain suppresses newer windows instead of stacking executions; a provably-dead chain must not wedge the schedule forever.
**Probe:** `tests/integration_tests/reports/commands_tests.py:3419-3461` (`test_new_crontab_window_skipped_while_retrying`) sets `retry_attempt=2`, old anchor, fresh `last_eval_dttm`, fires a command with a different dttm and asserts counter/state unchanged and no screenshot/retry calls; :3509-3542 (`test_is_retry_window_stale_naive_vs_aware`) pins aware-vs-naive equality as NOT stale and differing times as stale.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "retry window stale crontab anchor scheduled_dttm normalize", limit: 10 });
```

## Verdict
Adopt passing the originating trigger identity through the re-enqueue payload and treating anchor mismatch as "yield to new window"; adapt storage (any durable column works) but keep the normalization rule for mixed naive/aware clocks; omit Celery `apply_async` specifics and the max-delay liveness heuristic if your scheduler guarantees delivery. Coverage: source ranges read directly (:1502-1557, :1731-1754); direct tests read (:3419-3542); both files `no_recorded_issue`.
