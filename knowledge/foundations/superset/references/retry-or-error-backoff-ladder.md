<!-- capsule-v2 -->
# retry-or-error-backoff-ladder — What is the exact retry-then-error decision a failing state must run?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** When delivery/execution fails, how does one shared ladder decide between scheduling another attempt and falling through to terminal error handling — without ever masking the original exception?

## Shared retry-or-error funnel
**Path/Symbol:** `superset/commands/report/execute.py` — `_get_retry_delay` (:1502-1506), `send_retry_notification` (:1559-1596), `send_final_failure_report` (:1598-1613), `_handle_retry_or_error` (:1615-1685). Sole callers: `ReportNotTriggeredErrorState.next` :1797 and `ReportSuccessState.next` :1999 (verified via inbound trace).
**Signature:** `_handle_retry_or_error(self, error_message: str, original_exception: Exception) -> bool` — True ⇒ caller returns silently (retry scheduled); False ⇒ caller runs its own ERROR path.
**Data Shape:** schedule flags `retry_on_failure: bool`, `retry_max_attempts: int`, `retry_attempt: int`, `send_failed_reports: bool`, `retry_notify_owners/recipients: bool`; config `ALERT_REPORTS_RETRY_BASE_DELAY_SECONDS` (60) / `..._MAX_DELAY_SECONDS` (3600).

### Decisive source
```python
def _get_retry_delay(self, attempt: int) -> int:
    base = app.config.get("ALERT_REPORTS_RETRY_BASE_DELAY_SECONDS", 60)
    cap = app.config.get("ALERT_REPORTS_RETRY_MAX_DELAY_SECONDS", 3600)
    return min(base * (2**attempt), cap)

def _handle_retry_or_error(self, error_message, original_exception) -> bool:
    if not self._report_schedule.retry_on_failure:
        return False
    max_attempts = self._report_schedule.retry_max_attempts
    if self._is_retry_window_stale():
        self._reset_retry_counter()
    current_attempt = self._report_schedule.retry_attempt
    # Notify AFTER the attempt ran so the email reflects what happened.
    if current_attempt > 0:
        try:
            self.send_retry_notification(current_attempt, max_attempts, error_message)
        except Exception:
            logger.warning("Failed to send retry notification ...", exc_info=True)
    if current_attempt < max_attempts:
        self._increment_retry()
        try:
            self.update_report_schedule_and_log(ReportState.RETRYING, error_message=error_message)
        except ReportScheduleUnexpectedError as logging_ex:
            raise original_exception from logging_ex   # never hide the root cause
        self._schedule_retry(self._get_retry_delay(self._report_schedule.retry_attempt - 1))
        return True  # retry scheduled — caller should return
    self._reset_retry_counter()
    if self._report_schedule.send_failed_reports:
        try:
            self.send_final_failure_report(error_message)
        except Exception:
            logger.warning(...)
    return False  # exhausted — caller should handle error normally
```

**Flow:** gate on per-schedule opt-in → stale-window reset (see retry-window-staleness-anchor) → post-attempt notification only for attempts ≥1 (best-effort; its failure is swallowed) → budget remaining: increment counter, persist RETRYING (a DB failure here re-raises the **original** exception chained *from* the logging failure, never the logging error alone), re-enqueue with capped exponential countdown `min(base·2^(attempt-1), cap)`, return True so the state exits cleanly without raising → budget exhausted: reset counter, optional final-failure report to all recipients, return False so the caller's normal ERROR handling runs (log + grace-throttled owner notification).
**Invariant:** The boolean return is the contract — True means "no exception escapes this tick"; every notification/persistence side-path is best-effort except the RETRYING log write whose failure must chain from the original exception. Recipient selection for retry notices (`retry_notify_owners` → user-type editors; `retry_notify_recipients` → all recipients) defaults to silence when both unset.
**Probe:** `tests/integration_tests/reports/commands_tests.py:3153-3190` (`test_retry_on_failure_schedules_retry`) pins retry scheduled on first failure; :3197-3246 (`test_retry_exhausted_transitions_to_error`) pins exhaustion → ERROR transition; :3545-3562 pins `min(60·2^n, 3600)` arithmetic. Unit-side, `tests/unit_tests/commands/report/execute_test.py:3662-3683` pins success clearing persisted retry state.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "handle retry or error exhausted final failure report backoff", limit: 10 });
```

## Verdict
Adopt the boolean-outcome funnel with capped exponential backoff, post-attempt notification ordering, and "re-raise original chained-from logging failure"; adapt flag names/delay constants to your host; omit Celery countdown mechanics and Superset's DAO-based editor resolution. Coverage: source ranges read directly (:1502-1685); direct tests read at commands_tests.py:3419-3562 and execute_test.py:3662-3683; files `no_recorded_issue`.
