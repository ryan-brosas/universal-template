<!-- capsule-v2 -->
# Revoke plane — how does a task id get cancelled before and during execution?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What are the layers between "broadcast revoke" and "the process actually dies", and what states does the caller observe?

## Request.revoked / _announce_revoked / _announce_cancelled
**Path/Symbol:** `celery/worker/request.py:revoked` (:470-517), `_announce_revoked` (:498-513), `_announce_cancelled` (:452-469), `terminate` (:416), `cancel` (:428); storage side worker-state capsule (`revoked` LimitedSet, `revoked_stamps` dict); control entry points from control-panel capsule.
**Signature:** `revoked() -> bool` checked at strategy time AND inside execute paths; `terminate(pool, signal=None)` → if started: `pool.terminate_job(worker_pid, signum)` + announce; else stash `self._terminate_on_ack = (pool, signal)` to kill at accept time.
**Data Shape:** three revocation keys: task-id set (LimitedSet w/ expiry), stamped-header map `revoked_stamps[header] = [values]`, and expiry-based revocation (`expires` in the past → maybe_expire adds id to revoked_tasks).

### Decisive source
```python
# celery/worker/request.py:476-516 — the screening ladder
if self._already_revoked:
    return True
if self.expires:
    expired = self.maybe_expire()
revoked_by_id = self.id in revoked_tasks
revoked_by_header, revoking_header = False, None
if not revoked_by_id and self.stamped_headers:
    for stamp in self.stamped_headers:
        if stamp in revoked_stamps:
            ...match list-or-scalar stamp values...
            break
if any((expired, revoked_by_id, revoked_by_header)):
    info('Discarding revoked task: %s[%s]', ...)
    self._announce_revoked(
        'expired' if expired else 'revoked', False, None, expired)
    return True
```
```python
# :498-507 — announcement = event + backend state + ack
def _announce_revoked(self, reason, terminated, signum, expired):
    task_ready(self)
    self.send_event('task-revoked', terminated=..., signum=...,
                    expired=expired)
    self.task.backend.mark_as_revoked(self.id, reason,
                                      request=self._context,
                                      store_result=self.store_errors)
    self.acknowledge()
```

**Flow:** strategy checks `req.revoked()` before signals/handoff → discarding path announces (task-revoked event + REVOKED backend state + ack) without executing → for RUNNING tasks terminate kills the child via pool.terminate_job then announces; if the task hadn't been accepted yet the request is parked in `_terminate_on_ack` and killed at on_accepted → cancel() variant announces CANCELLED instead: emits task-cancelled event and optionally marks RETRY in the backend (`emit_retry`) so callers see a retryable outcome rather than failure.
**Invariant:** (1) Announce is exactly four actions in order — ready-transition, event, backend mark, ACK — omitting the ack leaks the delivery. (2) `_already_revoked/_already_cancelled` latches prevent double announcements when both control broadcast and shutdown drain hit. (3) Terminate-before-start must be deferred (kill-on-ack) or the pid doesn't exist yet. (4) Revokes expire (default ~1h): it's an anti-execution hint, not permanent deletion.
**Probe:** `t/unit/tasks/test_trace.py::test_worker_task_trace_handle_failure`-adjacent revoke tests plus `t/unit/worker/test_request.py::test_revoked_*` pins; end-to-end `t/unit/worker/test_revoke.py`.
**Retrieve:**
```json
{"project":"ext-celery","query":"_announce_revoked revoked_stamps terminate_on_ack","limit":5,"detail":"ids"}
```
## Verdict
Adopt: pre-execution screening ladder, four-step announcement, kill-on-ack deferral, cancelled-vs-revoked duality with emit_retry choice. Adapt pool.terminate_job and LimitedSet storage. Omit stamped-header group revocation unless your messages carry stamps.
