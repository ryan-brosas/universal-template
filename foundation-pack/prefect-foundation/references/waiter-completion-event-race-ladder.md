<!-- capsule-v2 -->

# Waiter completion-event race ladder — How do you wait for an async completion that may fire while you are still setting up the wait?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What check/register/re-check discipline closes the lost-wakeup race between a shared event consumer and a late waiter?

## Cache-check → loop-thread Event → register → RE-check → bounded wait → pop

**Path/Symbol:** `src/prefect/_internal/waiters.py:FlowRunWaiter.wait_for_flow_run (168-211)`; twin `src/prefect/task_runs.py:TaskRunWaiter.wait_for_task_run (175-226)`. Retrieve anchor: `wait_for_flow_run Method 168-211` (`^wait_for_flow_run$` returns both twins).

**Signature:** `async wait_for_flow_run(cls, flow_run_id: UUID, timeout: float | None = None) -> None` / `async wait_for_task_run(...) -> Optional[State]`.

**Data Shape:** `_observed_completed_*: TTLCache(maxsize=10_000, ttl=600)` of completions already seen; `_completion_events: dict[UUID, asyncio.Event]`; consumer side sets `event.set()` under `_completion_events_lock` when a terminal event arrives.

### Decisive source
```python
instance = cls.instance()
with instance._observed_completed_flow_runs_lock:
    if flow_run_id in instance._observed_completed_flow_runs:
        return                                    # 1: already completed
finished_event = await from_async.wait_for_call_in_loop_thread(
    create_call(asyncio.Event))                   # 2: create IN LOOP THREAD
with instance._completion_events_lock:
    instance._completion_events[flow_run_id] = finished_event   # 3: register
try:
    with instance._observed_completed_flow_runs_lock:
        if flow_run_id in instance._observed_completed_flow_runs:
            return                                # 4: re-check — it may have
                                                  #    landed during setup
    with anyio.move_on_after(delay=timeout):      # 5: bounded wait
        await from_async.wait_for_call_in_loop_thread(
            create_call(finished_event.wait))
finally:
    with instance._completion_events_lock:
        instance._completion_events.pop(flow_run_id, None)      # 6: cleanup
```

**Flow:** a single background consumer task fans terminal events into both the TTL cache and per-id asyncio.Events. A waiter must handle the interleaving where completion arrives between step 1 and step 5; the second cache check after registration closes exactly that window, so the worst case is one redundant wait, never a hang. The asyncio.Event is created ON THE GLOBAL LOOP THREAD because the consumer sets it from there — an Event bound to the caller's loop cannot be set cross-thread. Timeout uses anyio cancellation scope rather than checking elapsed time, and cleanup pops the registration even on timeout/cancel.

**Invariant:** (1) Register-then-recheck is mandatory: cache-check alone races, register alone hangs. (2) Cross-thread wakeup objects must be constructed in the waking thread's loop. (3) Late waiters are served from the TTL cache without touching the network — completion knowledge outlives the moment by ttl=600 s / 10k entries. TaskRunWaiter additionally RETURNS the terminal State rebuilt from `event.payload["validated_state"]`, or None on timeout via post-wait cache re-read.

**Probe:** direct tests `tests/test_waiters.py`: `:29-47 test_wait_for_flow_run` (real run + pipeline; fails by timeout if wake-up broken), `:49-61 test_wait_for_flow_run_with_timeout` (returns early, run still not done), `:87-129 test_handles_concurrent_task_runs` (two runs, waits independent). Twin: `tests/test_task_runs.py:26-60` same pair for tasks.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^wait_for_flow_run$", "limit": 5}'
```
(observed: exactly 2 rows — `FlowRunWaiter.wait_for_flow_run Method src/prefect/_internal/waiters.py 168-211` and `flow_runs.wait_for_flow_run Function src/prefect/flow_runs.py 57-158`; note `name_pattern "_observed_completed_flow_runs"` observed total: 0 — instance attrs have no graph nodes.)

## Verdict
Adopt the six-step race ladder verbatim for any fan-in completion bus; adapt cache sizing/TTL and what "completion payload" means; omit Prefect's specific locks-per-dict granularity if your host is single-loop.
