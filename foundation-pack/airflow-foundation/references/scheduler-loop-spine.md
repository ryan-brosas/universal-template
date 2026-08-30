<!-- capsule-v2 -->
# Scheduler loop spine — how do timed side-tasks run inside one scheduling loop without threads?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does one process interleave periodic janitorial jobs (orphan sweep, timeout checks, metrics) with the hot scheduling path, and what does each interval default actually control?

## EventScheduler timer fan-out around `_do_scheduling`
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:SchedulerJobRunner._run_scheduler_loop` (1785–1983); `airflow-core/src/airflow/utils/event_scheduler.py:EventScheduler.call_regular_interval` (29–66).
**Signature:** `_run_scheduler_loop(self) -> None`; `call_regular_interval(self, delay, action, *args, **kwargs) -> Timer`.
**Data Shape:** One infinite loop (`itertools.count(start=1)`); per iteration: `_do_scheduling(session)` → executor `heartbeat()` for every executor → `_process_executor_events` → deadline sweep (`with_row_locks ... skip_locked`) → `_enqueue_executor_callbacks` → `perform_heartbeat(job)` → `timers.run(blocking=False)`. Idle detection gates sleep: `time.sleep(min(self._scheduler_idle_sleep_time, next_event or 0))`.

### Decisive source
```python
timers.call_regular_interval(
    conf.getfloat("scheduler", "task_instance_heartbeat_timeout_detection_interval", fallback=10.0),
    self._find_and_purge_task_instances_without_heartbeats,
)
...
idle_in_this_run = not num_queued_tis and not num_finished_events
if not is_unit_test and idle_in_this_run:
    # If the scheduler is doing things, don't sleep. ...
    time.sleep(min(self._scheduler_idle_sleep_time, next_event or 0))
```

**Flow:** adopt-or-reset runs once at startup then on its own timer; every registered timer fires only when the main loop reaches `timers.run(blocking=False)` — timers never interrupt a scheduling pass; `num_runs` counts total loops unless `only_idle=True`, which counts only idle loops (counter resets to zero whenever work happened).
**Invariant:** A slow `_do_scheduling` delays ALL side-jobs (they are cooperative, not preemptive); an idle scheduler must still sleep at most until the next timer deadline so janitorial intervals stay honest.
**Probe:** `grep -c 'timers.call_regular_interval' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 14 registered intervals; direct test `airflow-core/tests/unit/utils/test_event_scheduler.py::TestEventScheduler::test_call_regular_interval`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "_run_scheduler_loop EventScheduler timers call_regular_interval", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-threaded cooperative-timer loop with idle-gated sleep and the startup-plus-interval pattern for orphan sweeps. Adapt interval values/config names to your host. Omit Airflow's stats/metrics emission wiring if you have no metrics backend.
