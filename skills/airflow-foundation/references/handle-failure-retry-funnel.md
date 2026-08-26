<!-- capsule-v2 -->
# handle_failure retry decision — where is the single place that decides FAILED vs UP_FOR_RETRY?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** On task failure, how do retry eligibility, history recording, and fail-fast interact?

## One funnel: `fetch_handle_failure_context` → `save_to_db`
**Path/Symbol:** `airflow-core/src/airflow/models/taskinstance.py:TaskInstance.fetch_handle_failure_context` (1882–1951); `handle_failure` (1962–1996); `is_eligible_to_retry` (1998–2012); `prepare_db_for_next_try` (1070–1076).
**Signature:** `handle_failure(self, error, test_mode=None, *, session)`; `is_eligible_to_retry(self) -> bool`.
**Data Shape:** Retry predicate: `RESTARTING ⇒ True` (cleared-while-running always retries); no loaded task ⇒ guess `try_number <= max_tries`; else `bool(task.retries and self.try_number <= self.max_tries)`.

### Decisive source
```python
if not ti.is_eligible_to_retry():
    ti.state = TaskInstanceState.FAILED
    if task and fail_fast:
        _stop_remaining_tasks(task_instance=ti, session=session)
else:
    if ti.state == TaskInstanceState.RUNNING:
        # If the task instance is in the running state, ... record the task instance history.
        ti.prepare_db_for_next_try(session)
    ti.state = State.UP_FOR_RETRY
```

**Flow:** refresh from DB → set end_date/duration → metrics/logs → `clear_next_method_args()` (deferral resume state MUST NOT leak into the retry) → branch above → listener hook (exception-swallowed) → merge+flush+commit. `prepare_db_for_next_try` snapshots the row into TaskInstanceHistory (audit of the abandoned attempt), deletes TaskReschedule rows, and rotates `ti.id = uuid7()` — a new PK per attempt so history rows never collide.
**Invariant:** History must be recorded BEFORE the new attempt starts and only for failures originating from RUNNING; cleared (non-running) retries were already recorded at clear time — double-record here would corrupt the audit trail. Scheduler-side callers that pre-compute callback type must call THIS predicate (`is_eligible_to_retry`), not reimplement it, or callbacks disagree with persisted state.
**Probe:** `grep -c 'prepare_db_for_next_try' airflow-core/src/airflow/models/taskinstance.py` → 3; direct test `test_handle_failure_fail_fast` at `airflow-core/tests/unit/models/test_taskinstance.py:2462`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "handle_failure is_eligible_to_retry up_for_retry max_tries fail_fast", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-funnel failure handler with history-before-retry and PK rotation per attempt. Adapt uuid7 to your id scheme (any fresh unique key works). Omit fail_fast downstream-stopping if your model lacks DAG-level circuit breaking.
