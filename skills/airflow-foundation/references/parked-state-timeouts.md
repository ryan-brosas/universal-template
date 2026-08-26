<!-- capsule-v2 -->
# Deferred-task timeout sweeps — trigger timeout as a bulk UPDATE; HITL timeouts with a response race window

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How do parked DEFERRED/AWAITING_INPUT tasks get unstuck when their deadline passes, and how is a just-in-time user response honored?

## Two different sweep shapes for two parked states
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:check_trigger_timeouts` (3489–3511), `check_awaiting_input_timeouts` (3514–3613).
**Signature:** both on `trigger_timeout_check_interval` (15s) timers, wrapped in `run_with_db_retries`.
**Data Shape:** Trigger sweep = one bulk UPDATE over `state=DEFERRED ∧ trigger_timeout < now` → SCHEDULED with `next_method="__fail__"`, `next_kwargs={"error": TriggerFailureReason.TRIGGER_TIMEOUT}`, `trigger_id=None`. HITL sweep = row-locked SELECT LIMIT 100 with three branches.

### Decisive source
```python
if hitl_detail is not None and hitl_detail.responded_at is not None:
    # A response landed just before the deadline; resume with it.
    handle_event_submit(TriggerEvent(hitl_detail.as_resume_event_payload(timedout=False)), ...)
elif hitl_detail is not None and hitl_detail.defaults is not None:
    # Apply the configured defaults as the response, then resume to success.
    hitl_detail.chosen_options = list(hitl_detail.defaults)
    ...
else:
    # resume into execute_complete with a timeout failure event so the operator raises HITLTimeoutError
    handle_event_submit(TriggerEvent({"error": "...response timeout has passed...", "error_type": "timeout"}), ...)
```

**Flow:** DEFERRED tasks fail wholesale via SQL (their resume protocol already understands __fail__). AWAITING_INPUT needs row-level arbitration: lock only TI rows (`of=TI`) so the FOR UPDATE isn't applied to the nullable side of the hitl_detail outer join; batch capped at 100 per tick so one scheduler can't hold an unbounded backlog and block concurrent responses/clears; branch order = response-beats-timeout, defaults-resume-to-success, else synthetic timeout TriggerEvent routed through execute_complete so operators raise their OWN timeout error type rather than a generic deferral failure.
**Invariant:** The response-vs-deadline race resolves in favor of the USER whenever `responded_at` is set, even past deadline; unresumable outcomes (`handle_event_submit` routing to __fail__) are counted separately from intentional failures. Bulk SQL is only safe where no per-row decision exists.
**Probe:** `grep -c 'AWAITING_INPUT' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 6; direct tests `test_awaiting_input_timeout_with_defaults_resumes` (:8146) and `test_zombies_detected_heartbeat_timeout_emitted` (:13977 for metrics adjacency) in `airflow-core/tests/unit/jobs/test_scheduler_job.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "check_awaiting_input_timeouts AWAITING_INPUT limit 100 with_row_locks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bulk-SQL sweeps for machine-parked states and locked bounded batches with priority-to-response for human waits. Adapt the branch semantics to your approval workflow. Omit HITL detail persistence specifics.
