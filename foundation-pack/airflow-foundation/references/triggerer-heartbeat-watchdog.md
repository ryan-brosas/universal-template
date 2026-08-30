<!-- capsule-v2 -->
# Triggerer heartbeat watchdog — why would a healthy process deliberately skip its own heartbeat?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does the supervisor detect a deadlocked async runner subprocess and force failover of its triggers?

## Withhold `perform_heartbeat` while subprocess comms are silent past threshold
**Path/Symbol:** `airflow-core/src/airflow/jobs/triggerer_job_runner.py:TriggerRunnerSupervisor.heartbeat` (723–742); run loop `run`/`run_once` (691–721).
**Signature:** `heartbeat(self)`; `run_once(self)`: load_triggers → `_service_subprocess(1)` → handle_events → handle_failed_triggers → clean_unused → heartbeat → emit_metrics.
**Data Shape:** `_last_runner_comms: float` (monotonic, updated wherever a message arrives from the subprocess); `runner_health_check_threshold` (config; 0 disables the watchdog); `_runner_comms_silence_logged: bool` arms ONCE.

### Decisive source
```python
elapsed = time.monotonic() - self._last_runner_comms
if self.runner_health_check_threshold > 0 and elapsed > self.runner_health_check_threshold:
    if not self._runner_comms_silence_logged:
        log.error("TriggerRunner subprocess event loop appears deadlocked: ... Skipping heartbeat so the triggerer appears unhealthy to the scheduler and its triggers are reassigned.", ...)
        self._runner_comms_silence_logged = True
    return
self._runner_comms_silence_logged = False
perform_heartbeat(self.job, heartbeat_callback=self.heartbeat_callback, only_if_necessary=True)
```

**Flow:** every loop tick (~1s) services the subprocess; if no comms for >threshold, heartbeat is SKIPPED so `Job.latest_heartbeat` goes stale → scheduler's liveness queries (`alive_triggerer_ids`, orphan sweeps) stop counting this triggerer alive → `Trigger.assign_unassigned` on ANOTHER triggerer claims its rows (they match "triggerer_id not in alive ids"). Silence flag ensures one error log per incident; recovery resets it.
**Invariant:** The supervisor must NOT keep heartbeating while its runner is wedged — that would look healthy forever and defer tasks would hang indefinitely. The watchdog converts an internal deadlock into an externally visible health failure using the EXISTING heartbeat-liveness channel instead of a new protocol.
**Probe:** `grep -c '_runner_comms_silence_logged' airflow-core/src/airflow/jobs/triggerer_job_runner.py` → 4; direct tests `test_heartbeat_watchdog` (:512) + `test_heartbeat_watchdog_disabled_when_threshold_is_zero` (:547) in `airflow-core/tests/unit/jobs/test_triggerer_job.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "triggerer heartbeat watchdog runner comms silence subprocess deadlock", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt silence-based health withholding as failover signal for supervised event loops. Adapt the threshold source (default 30s class). Omit AIP-92 subclass hooks if you have no execution-API variant.
