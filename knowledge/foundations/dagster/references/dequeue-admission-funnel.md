<!-- capsule-v2 -->
# Queued-run dequeue admission funnel — how does the run queue pick which QUEUED runs may launch this tick?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** Given a global max, tag limits, and priority tags, in what order are queued runs filtered and how is FIFO preserved?

## Priority-stable sort inside a paginated filter sweep
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/run_coordinator/queued_run_coordinator_daemon.py:_get_runs_to_dequeue` (lines 192-340) + `_priority_sort` (:345-354) + `_dequeue_run` (:363-492).
**Signature:** `def _get_runs_to_dequeue(self, instance: DagsterInstance, concurrency_config: ConcurrencyConfig, fixed_iteration_time: float | None) -> list[DagsterRun]`; `PAGE_SIZE = int(os.getenv("DAGSTER_RUN_QUEUE_PAGE_SIZE", "100"))`.
**Data Shape:** Input: runs with status QUEUED read cursor-paginated (`instance.get_runs(RunsFilter(statuses=[QUEUED]), cursor=..., limit=PAGE_SIZE, ascending=True)` — ascending run-id order = submission order); in-progress records fetched once per iteration via `_get_in_progress_run_records` (statuses IN_PROGRESS_RUN_STATUSES). `max_concurrent_runs == -1` disables the global limit.

### Decisive source
```python
def _priority_sort(self, runs: Iterable[DagsterRun]) -> list[DagsterRun]:
    def get_priority(run: DagsterRun) -> int:
        priority_tag_value = run.tags.get(PRIORITY_TAG, "0")
        try:
            return int(priority_tag_value)
        except ValueError:
            return 0

    # sorted is stable, so fifo is maintained
    return sorted(runs, key=get_priority, reverse=True)
```
And the per-batch block/filter loop (:301-338): a run is dropped if `tag_concurrency_limits_counter.is_blocked(run)` (else its counters are incremented via `update_counters_with_launched_item(run)` — greedy in-place accounting), if the global op-concurrency counter blocks it (first time only, recorded in `_global_concurrency_blocked_runs` + debug info log), or if its code location is in `_location_timeouts` (paused after user-code errors). Only then `batch = batch[:max_runs_to_launch]`.

**Flow:** compute `max_runs_to_launch = max_concurrent_runs - len(in_progress_records)`, bail at ≤0 → paginate QUEUED runs ascending → re-sort accumulated batch by priority (STABLE sort ⇒ equal priorities keep FIFO; malformed priority tags parse as "0" instead of raising — pinned by test_priority_on_malformed_tag) → drop tag-blocked / global-concurrency-blocked / paused-location runs → truncate to `max_runs_to_launch` → each survivor re-checked in `_dequeue_run`: re-fetch by id ("double check that the run is still queued before dequeuing"), skip if status moved off QUEUED, emit PIPELINE_STARTING event, call `run_launcher.launch_run`.
**Invariant:** The stable-sort + truncation ordering means capacity goes to highest-priority-first, oldest-within-priority; dropping happens BEFORE truncation so blocked high-priority runs don't consume slots that lower-priority runnable runs could use. The queue is re-derived from storage every tick — there is no in-memory queue to lose on daemon restart.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_queued_run_coordinator_daemon.py::QueuedRunCoordinatorDaemonTests.test_priority` (:307), `test_priority_on_malformed_tag` (:339), `test_key_limit_with_priority` (:1046).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_get_runs_to_dequeue _priority_sort TagConcurrencyLimitsCounter", limit: 10 });
```

## Verdict
Adopt stable-priority-sort-over-FIFO + greedy counter decrement + re-check-before-launch; adapt tag vocabulary (`dagster/priority`) and page size; omit the helm-template config surface. Direct tests exist for all three cited behaviors.
