<!-- capsule-v2 -->
# create-log-working-row-promotion — Why does one execution surface as exactly one log row?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A run writes a WORKING row at start and a terminal row at end — how do you keep that from becoming two rows in the user-facing execution log?

## WORKING trigger-row promotion
**Path/Symbol:** `superset/commands/report/execute.py:create_log` (:418-494) with `update_report_schedule_and_log` (:368-394).
**Signature:** `create_log(self, error_message: Optional[str] = None, *, include_execution_warnings: bool = True, log_state: ReportState | None = None, reuse_working_log: bool = True) -> None`.
**Data Shape:** `ReportExecutionLog(uuid=execution_id, state, error_message, end_dttm, value, value_row_json)`; promotion query filters `uuid == self._execution_id ∧ state == WORKING ∧ error_message IS NULL`.

### Decisive source
```python
# Reuse the in-flight WORKING trigger row for this execution, if any,
# so a single execution surfaces as a single log entry.
effective_state = log_state or self._report_schedule.last_state
log = (
    db.session.query(ReportExecutionLog)
    .filter(
        ReportExecutionLog.uuid == self._execution_id,
        ReportExecutionLog.state == ReportState.WORKING,
        ReportExecutionLog.error_message.is_(None),
    )
    .first()
    if reuse_working_log and effective_state != ReportState.WORKING
    else None
)
if log is None:
    log = ReportExecutionLog(scheduled_dttm=..., start_dttm=..., report_schedule=..., uuid=self._execution_id)
    db.session.add(log)
log.end_dttm = ...
log.state = effective_state
log.error_message = log_message
db.session.commit()
```

**Flow:** every transition goes through `update_report_schedule_and_log(state, error_message?)` which mutates the schedule (`last_state`, `last_eval_dttm`; WORKING additionally clears `last_value`/`last_value_row_json` so stale alert values never propagate into logs) then calls `create_log`. Terminal write: find this execution's own WORKING placeholder row → promote it in place (rewrite state/error/end_dttm) instead of inserting row #2 (#29857). Exceptions: `error_message == REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER` is logged verbatim (warnings deliberately *not* joined — the grace-period dedup queries match on the exact marker); otherwise warnings + error are joined with `";"`. `include_execution_warnings=False` serves secondary error rows.
**Invariant:** One execution uuid ⇒ one user-visible row for its lifecycle; promotion is keyed by the execution's own uuid only (never another run's). Marker rows and refused-duplicate rows (`reuse_working_log=False`, `log_state=` override) are intentionally distinct inserts. `StaleDataError` (schedule deleted/modified mid-run) rolls back and re-raises as typed `ReportScheduleUnexpectedError`.
**Probe:** `tests/unit_tests/commands/report/execute_test.py:3854-3878` pins insert-when-no-working-row; :3881-3903 pins warning+error join `"Slack v1 fallback is deprecated;Email delivery failed"` onto a promoted row; :3906-3929 pins marker preserved verbatim without warnings; :3932-3958 pins `include_execution_warnings=False`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "create_log reuse working log promote terminal state single row", limit: 10 });
```

## Verdict
Adopt placeholder-row promotion keyed by an execution-scoped id so start/end writes collapse to one audit record; adapt row schema/marker vocabulary; omit StaleDataError specifics but map your own concurrent-modification error to something typed. Coverage: source ranges read directly (:368-494); direct tests read (:3854-3958); file `no_recorded_issue`.
