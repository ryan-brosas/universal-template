<!-- capsule-v2 -->
# Scheduler-side defer_task — how does a task defer BEFORE ever reaching a worker?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How do `start_trigger_args` operators skip worker execution entirely and park on the triggerer at scheduling time?

## Trigger row first, TI mutation second, timeout = min(execution_timeout, trigger timeout)
**Path/Symbol:** `airflow-core/src/airflow/models/taskinstance.py:TaskInstance.defer_task` (1819–1879).
**Signature:** `defer_task(self, *, session) -> bool` (False = no start_trigger_args, proceed to normal execution).
**Data Shape:** Reads `start_trigger_args` (`trigger_cls`, `trigger_kwargs`, `timeout`, `next_method`, `next_kwargs`); sets `trigger_id`, `next_method`, `next_kwargs` (stringify_encoding_keys'd), `state=DEFERRED`, resets `start_date=now`.

### Decisive source
```python
# If an execution_timeout is set, set the timeout to the minimum of
# it and the trigger timeout
if execution_timeout := self.task.execution_timeout:
    if self.trigger_timeout:
        self.trigger_timeout = min(self.start_date + execution_timeout, self.trigger_timeout)
    else:
        self.trigger_timeout = self.start_date + execution_timeout
if pre_deferral_state != TaskInstanceState.UP_FOR_RESCHEDULE:
    self.try_number += 1
```

**Flow:** called from `schedule_tis` for each schedulable TI → create+flush Trigger row (Fernet-encrypted kwargs) → flip TI to DEFERRED with pointer → clamp `trigger_timeout` by the operator's `execution_timeout` (the effective deadline is ALWAYS the earlier of the two) → increment try_number EXCEPT when deferring from UP_FOR_RESCHEDULE (reschedule sensors must not burn tries per poll). The comment warns to keep this consistent with `check_and_change_state_before_execution`'s next_method semantics.
**Invariant:** The trigger row is created and flushed BEFORE the TI references it (FK integrity); try_number accounting must mirror the reschedule-sensor rule or sensors accumulate phantom retries; `trigger_timeout` doubles as the sweep key for `check_trigger_timeouts`.
**Probe:** `grep -c 'try_number += 1' airflow-core/src/airflow/models/taskinstance.py` → 1; direct tests `test_defer_task_with_trigger_timeout` (:2963) and `test_defer_task_returns_false_when_no_start_trigger_args` (:2892) in `airflow-core/tests/unit/models/test_taskinstance.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "defer_task start_trigger_args trigger_timeout execution_timeout min", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt schedule-time deferral for operators that declare an async entry point, including the min-timeout clamp. Adapt the trigger persistence model. Omit multi-team trigger tagging.
