<!-- capsule-v2 -->
# Beat heap scheduler — how does a cron-like scheduler tick exactly-once per entry without blocking the heap?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How does tick() decide what's due, avoid double-fires under heap mutation, and handle entries whose schedule says "not yet" after the heap said "now"?

## Scheduler.tick
**Path/Symbol:** `celery/beat.py:Scheduler.tick` (:326-376), `populate_heap` (:310), `_when` (:300), `reserve` (:404), `apply_async` (:408-441), `should_sync` (:396); driver loop `celery/beat.py:Service.start` (:653-675); persistence `PersistentScheduler.setup_schedule` (:551-587; class `PersistentScheduler` begins :525).
**Signature:** `tick(event_t=event_t, min=min, heappop=heapq.heappop, heappush=heapq.heappush) -> float` (sleep hint seconds); heap items are `(utc_timestamp, priority, entry)` with priority fixed at 5.
**Data Shape:** `self._heap: list[event_t]`; `self.schedule: dict[name, entry]`; entry carries `last_run_at`, `total_run_count`, `schedule` (BaseSchedule with is_due → `(bool, next_seconds)`).

### Decisive source
```python
# celery/beat.py:344-376 — one due entry per call, identity-checked
event = H[0]
entry = event[2]
now = self._when(entry, 0)
if event[0] > now:
    return min(event[0] - now, max_interval)      # nothing due: sleep hint
is_due, next_time_to_run = self.is_due(entry)
if is_due:
    verify = heappop(H)
    if verify is event:                            # identity guard vs mutation
        next_entry = self.reserve(entry)
        self.apply_entry(entry, producer=self.producer)
        heappush(H, event_t(self._when(next_entry, next_time_to_run),
                            event[1], next_entry))
        return 0                                   # another may be due now
    else:
        heappush(H, verify)
        return min(verify[0], max_interval)

# Heap said ready but schedule says retry later (#7649): REHEAP it,
# else it sits on top forever and starves the entries behind it.
reschedule_delay = next_time_to_run if is_numeric_value(...) else max_interval
verify = heappop(H)
if verify is event:
    heappush(H, event_t(self._when(entry, reschedule_delay), event[1], entry))
    return 0 if H and H[0][2] is not entry else min(...)
```

**Flow:** heap rebuilt whenever the schedule dict changed (`schedules_equal` compares keys AND editable-field equality) → peek top; not-yet-due returns sleep hint capped by max_interval (also the poll ceiling for external schedule changes) → due path: pop with identity verification, `reserve()` advances last_run_at/count BEFORE dispatch so a crash mid-send can't loop-fire forever, push next occurrence, return 0 to immediately re-check → not-due-despite-heap path re-heaps at the schedule's own delay → service loop sleeps the hint then `should_sync()` flushes shelve by time (sync_every) or task count (sync_every_tasks).
**Invariant:** (1) Exactly ONE entry fires per tick — returning 0 makes the loop spin back for more without recursion. (2) The `verify is event` identity check defends against concurrent heap mutation between peek and pop. (3) reserve-before-apply is the anti-thundering-herd rule. (4) A non-due top entry MUST be re-heaped or it blocks every later entry (#7649). (5) PersistentScheduler wipes its db when tz or utc_enabled changed — stale last_run_at across a tz switch corrupts all schedules.
**Probe:** `t/unit/app/test_beat.py::test_not_due_top_entry_is_rescheduled_behind_due_entry` (:450) pins #7649; `test_reheap_skipped_when_is_due_mutates_heap` (:467) pins the identity guard.
**Retrieve:**
```json
{"project":"ext-celery","query":"Scheduler.tick populate_heap reserve apply_entry","limit":5,"detail":"ids"}
```
## Verdict
Adopt: single-pop ticks, identity-guarded pops, reserve-before-dispatch, reheap-not-block, and the two-key sync policy. Adapt shelve persistence and event_t tuples to your store. Omit django-celery-beat-style external schedulers — this capsule is the embedded kernel only.
