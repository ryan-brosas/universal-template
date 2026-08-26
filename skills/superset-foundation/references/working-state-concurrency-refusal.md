<!-- capsule-v2 -->
# working-state-concurrency-refusal — How does a second tick behave when the previous execution is still WORKING?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** How do you block duplicate execution while a run is in flight, and how does a *recovery* tick unblock a schedule without mutating a possibly-still-alive worker's audit row?

## Concurrency guard state
**Path/Symbol:** `superset/commands/report/execute.py:ReportWorkingState.next` (:1856-1919) + `BaseReportState.is_on_working_timeout` (:1687-1713).
**Signature:** `next(self) -> None` (raises `ReportScheduleWorkingTimeoutError` | `ReportSchedulePreviousWorkingError`); `is_on_working_timeout(self) -> bool`.
**Data Shape:** `ReportSchedule.working_timeout: int | None`; `last_eval_dttm` naive datetime; `ReportScheduleDAO.find_last_entered_working_log(schedule) -> ReportExecutionLog | None`. For REPORT types the effective budget is `resolve_report_execution_budget_seconds(app.config, working_timeout=...)` — the same number enforcement uses.

### Decisive source
```python
def next(self) -> None:
    if self.is_on_working_timeout():
        ...
        exception_timeout = ReportScheduleWorkingTimeoutError()
        # Keep recovery owned by this invocation. If it reuses the original
        # execution id, create_log promotes that exact WORKING row. A distinct
        # invocation must not mutate the old audit row: Celery hard limits do
        # not preempt every worker pool, so the original worker may still be
        # alive. The recovery ERROR still unblocks the schedule without risking
        # a lost update or uncertain duplicate delivery.
        self.update_report_schedule_and_log(
            ReportState.ERROR,
            error_message=str(exception_timeout),
        )
        raise exception_timeout
    logger.warning(
        "Report still in working state, refusing to re-compute - execution_id: %s", ...)
    exception_working = ReportSchedulePreviousWorkingError()
    # This invocation is terminal even though the active owner's schedule
    # must remain WORKING. Record a distinct ERROR audit row rather than
    # accumulating another WORKING row or unblocking the active schedule.
    self.create_log(
        error_message=str(exception_working),
        log_state=ReportState.ERROR,
        reuse_working_log=False,
    )
    raise exception_working
```

**Flow:** dispatch lands here whenever `last_state == WORKING` → timeout probe against the last entered-WORKING log row → **timed out**: write ERROR to schedule + log (this is the recovery that unblocks the schedule; the old worker's own terminal write will lose the ownership race safely), raise WorkingTimeoutError → **not timed out**: leave the schedule owned by the active worker, record only a distinct ERROR audit row for *this* refused invocation (`log_state=` overrides the schedule's state; `reuse_working_log=False` forbids promoting any in-flight WORKING trigger row), raise PreviousWorkingError.
**Invariant:** While an execution owns `last_state == WORKING`, no other tick may recompute or deliver. Recovery (timeout) is the only path that flips the schedule out of WORKING, and it must not touch the original execution's audit row content — ownership is decided by comparing execution uuids inside `persist_owned_report_execution_terminal_error` (:191-291), which also guards "latest active WORKING row" before writing.
**Probe:** `tests/unit_tests/commands/report/execute_test.py:3423-3443` pins timeout → single `update_report_schedule_and_log(ERROR, str(WorkingTimeoutError()))` call; :3446-3461 pins not-timed-out → exactly one `create_log(error_message=str(PreviousWorkingError()), log_state=ERROR, reuse_working_log=False)` and no schedule mutation.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "working timeout previous working refuse recompute error log", limit: 10 });
```

## Verdict
Adopt the two-outcome guard: timeout ⇒ recover by terminalizing; not-timed-out ⇒ refuse with a side audit row while preserving the owner's state; adapt the budget source (Superset unifies stale-detection and enforcement on one resolved number); omit Celery-specific soft-limit commentary but keep the "old worker may still be alive" assumption. Coverage: source ranges read directly at :1856-1919 and :1687-1713; direct tests read at :3423-3514; file `no_recorded_issue`.
