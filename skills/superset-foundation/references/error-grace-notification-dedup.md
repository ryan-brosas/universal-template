<!-- capsule-v2 -->
# error-grace-notification-dedup — How do you notify owners once per failure streak instead of on every tick?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A schedule fails repeatedly; how does the executor send one error email per failure streak — and only when the notification actually went out?

## Marker-row grace throttle
**Path/Symbol:** `superset/commands/report/execute.py:is_in_error_grace_period` (:1485-1500) + `superset/daos/report.py:ReportScheduleDAO.find_last_error_notification` (:342-373); marker semantics in `create_log` (:444-451) and both state classes' error paths (:1817-1853, :2024-2055).
**Signature:** `is_in_error_grace_period(self) -> bool`; `find_last_error_notification(report_schedule) -> ReportExecutionLog | None`.
**Data Shape:** marker constant `REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER` stored verbatim in `ReportExecutionLog.error_message`; `grace_period: int | None` seconds; log rows carry `state`, `end_dttm`.

### Decisive source
```python
def find_last_error_notification(report_schedule):
    last_error_email_log = (
        db.session.query(ReportExecutionLog)
        .filter(
            ReportExecutionLog.error_message == REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER,
            ReportExecutionLog.report_schedule == report_schedule,
        )
        .order_by(ReportExecutionLog.end_dttm.desc())
        .first()
    )
    if not last_error_email_log:
        return None
    # Checks that only errors have occurred since the last email
    report_from_last_email = (
        db.session.query(ReportExecutionLog)
        .filter(
            ReportExecutionLog.state.notin_([ReportState.ERROR, ReportState.WORKING]),
            ReportExecutionLog.report_schedule == report_schedule,
            ReportExecutionLog.end_dttm < last_error_email_log.end_dttm,
        )
        ...
    )
    return last_error_email_log if not report_from_last_email else None
```

**Flow:** a state's generic-failure path logs ERROR first, then (outside grace) calls `send_error(...)` to user-type editors only → in the success-state variant the placeholder marker is recorded **only if** delivery actually succeeded; a send failure *overwrites* the marker with the real failure message so the dedup never believes a notification happened (:1959-1967, pinned by test) → next tick consults `is_in_error_grace_period`: DAO finds the newest marker row and returns it only if **no non-ERROR/non-WORKING row exists after it** (i.e. no success intervened since that email) → inside grace ⇒ skip the email but still persist ERROR; outside ⇒ notify again.
**Invariant:** One owner notification per failure streak; any intervening SUCCESS resets throttling. The marker must be written only on verified delivery — writing it speculatively would silence future notifications. The marker string is matched by exact equality, which is why execution warnings are deliberately excluded from that row (`create_log` special-cases it).
**Probe:** `tests/unit_tests/commands/report/execute_test.py:4304-4326` pins in-grace ⇒ `send_error` NOT called while ERROR still logged; :4336-4393 pins send-failure overwriting the marker with `"smtp down"` / `"smtp down;retry failed"`; :3906-3929 pins warnings never contaminating the marker row.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "error notification grace period last marker find_last_error_notification", limit: 10 });
```

## Verdict
Adopt query-based streak detection over in-memory counters (survives worker restarts) plus write-marker-only-on-verified-delivery; adapt what counts as "success intervenes" to your state vocabulary; omit FAB editor/SubjectType plumbing. Coverage: source ranges read directly (execute.py :1485-1500, :1942-1987, daos/report.py :342-373); direct tests read at execute_test.py:4304-4393, 3906-3929; files `no_recorded_issue`.
