<!-- capsule-v2 -->

# Local set_state bookkeeping — What must update atomically when a task run changes state without a server?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** Which denormalized fields and derived metrics must move TOGETHER on every state transition, and what timestamp hazard must be defused?

## Timestamp uniqueness + predictive denormalization + event chain

**Path/Symbol:** `src/prefect/task_engine.py:SyncTaskRunEngine.set_state (556-605)`; async twin `1181-1232`.

**Signature:** `set_state(self, state: State[R], force: bool = False) -> State[R]` — note: LOCAL mutation + event emission only; the FLOW engine's `set_state` instead proposes through the server API (`propose_state_sync`).

**Data Shape:** Mutates the TaskRun in place: `state`, `state_id`, `state_type`, `state_name`, `total_run_time`, `run_count`, `end_time`; returns the new State; carries `self._last_event` for event `follows` chaining.

### Decisive source
```python
if last_state.timestamp == new_state.timestamp:
    # Ensure that the state timestamp is unique ... This might occur
    # especially on Windows where the timestamp resolution is limited.
    new_state.timestamp += timedelta(microseconds=1)
...
if last_state.is_running():
    self.task_run.total_run_time += new_state.timestamp - last_state.timestamp
if new_state.is_running():
    self.task_run.run_count += 1
```

**Flow:** capture last state → assign new → enforce strictly-increasing timestamps (+1µs on collision, Windows clock-resolution defense) → backfill `state_details.task_run_id/flow_run_id` → mirror into the four denormalized columns → accumulate `total_run_time` ONLY when leaving Running → increment `run_count` when ENTERING Running (retries therefore inflate run_count by design) → on final states: stamp end_time once (`start_time and not end_time`) and link result for dependency tracking → emit state-change event with `follows=self._last_event` so the server-side event stream stays ordered.

**Invariant:** (1) Timestamp monotonicity is enforced client-side because downstream arithmetic (total_run_time, scheduling) silently breaks on equal timestamps; the +1µs bump must happen BEFORE any duration math uses the new timestamp. (2) total_run_time accrues on TRANSITIONS OUT of Running only — accruing on entry double-counts retries' idle time. (3) The Pending→(NotReady) path never goes through here with force=False semantics from begin_run: NotReady proposals pass `force=self.state.is_pending()` to re-force orchestration naming (flow engine). (4) Every emission chains via follows — dropping `_last_event` breaks causal ordering in the events pipeline.

**Probe:** `grep -c 'timedelta(microseconds=1)' src/prefect/task_engine.py` → 2 (sync+async). Direct tests: `tests/test_task_engine.py:102 test_set_task_run_state_duplicated_timestamp` (equal timestamps forced apart: `new_state.timestamp > running_state.timestamp`) and `tests/test_task_engine.py:1485 TestTaskTimeTracking` (e.g. :1787 test_sync_tasks_have_correct_total_run_time_with_retries asserting exact deltas).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "set_state timestamp microsecond unique total_run_time", "limit": 4}'
```

## Verdict
Adopt the transition-bookkeeping checklist (unique-ts → backfill ids → denormalize → accrue-on-exit → count-on-enter → single end_time → chained events) for any local-first run ledger; adapt field names; omit the event-schema specifics.
