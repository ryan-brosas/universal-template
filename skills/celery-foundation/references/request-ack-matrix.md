<!-- capsule-v2 -->
# Request ack/reject matrix — for every failure class, does the message get acked, rejected, or requeued?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** Given acks_late on/off and every terminal exception type, which of acknowledge/reject(requeue)/reject(no-requeue) runs — the single most mis-ported table in a task queue?

## Request lifecycle callbacks
**Path/Symbol:** `celery/worker/request.py:Request.execute` (:374), `on_accepted` (:536), `execute_using_pool` (:341), `on_timeout` (:416), `on_success` (:617), `on_retry` (:624), `on_failure` (:631-725), `acknowledge`/`reject` (:726-737).
**Signature:** pool callbacks: `accept_callback=self.on_accepted`, `timeout_callback=self.on_timeout`, `callback=self.on_success`, `error_callback=self.on_failure`; all idempotent via `self.acknowledged` latch.
**Data Shape:** Task flags: `acks_late` (ack after execution vs on receipt), `acks_on_failure`, `acks_on_timeout`, `reject_on_worker_lost`; exception taxonomy inspected with isinstance in fixed order.

### Decisive source
```python
# celery/worker/request.py:691-708 — the late-ack decision table
requeue = False
is_worker_lost = isinstance(exc, WorkerLostError)
if self.task.acks_late:
    is_timeout = isinstance(exc, TimeLimitExceeded)
    ack_flag = self.task.acks_on_timeout if is_timeout else self.task.acks_on_failure
    reject = (
        (self.task.reject_on_worker_lost and is_worker_lost)
        or (is_timeout and not ack_flag)
    )
    if reject:
        requeue = True
        self.reject(requeue=requeue)          # redeliver to someone else
        send_failed_event = False
    elif ack_flag:
        self.acknowledge()                     # swallow the failure
    else:
        self.reject(requeue=False)             # drop from local queue
```
```python
# celery/worker/request.py:645-663 — Reject without requeue = terminal FAILURE (#4222)
elif isinstance(exc, Reject):
    if not exc.requeue:
        self.task.backend.mark_as_failure(self.id, exc, ...)
        signals.task_failure.send(...)
    return self.reject(requeue=exc.requeue)
elif isinstance(exc, Ignore):
    return self.acknowledge()
elif isinstance(exc, Retry):
    return self.on_retry(exc_info)             # acks_late → ack here
```

**Flow:** early-ack mode acknowledges inside `execute()` (sync path) / `on_accepted()` (pool path) BEFORE execution; late mode defers to the outcome handlers above. Hard timeout path (`on_timeout(soft=False)`) is special: it marks FAILURE in backend, replays `task.on_failure` + errback-ish signal + task-failed event inline (because the child process is being killed and will report nothing), skips everything when `state.should_terminate` (cold shutdown), then late-acks per `acks_on_timeout` else `reject(requeue=True)`; it also nulls `exc.__traceback__` instead of calling `traceback_clear` — clearing the executing frame's own traceback raises RuntimeError that was silently swallowed.
**Invariant:** (1) Ack/reject are latched (`if not self.acknowledged`) — double-acking a delivery tag raises on the broker. (2) A non-requeue Reject must record terminal FAILURE or the task id sits in PENDING forever (#4222). (3) Worker-lost only requeues when `reject_on_worker_lost` is set; otherwise it's marked failed — at-least-once is opt-in per task. (4) Terminated tasks route through `_announce_revoked` not the normal failure path; MemoryError re-raised. (5) On cold shutdown `should_terminate` suppresses backend/event writes (process may die mid-write).
**Probe:** `t/unit/worker/test_request.py` pins each row: `test_on_retry_acks_if_late` (:270), `test_on_failure_Ignore_acknowledges` (:301), `test_on_failure_Reject_rejects` (:312), `test_on_failure_Reject_marks_as_failure` (:326), `test_on_failure_WorkerLostError_rejects_with_requeue` (:416), `test_on_failure_TimeLimitExceeded_acks` (:481), `test_on_failure_TimeLimitExceeded_rejects_with_requeue` (:504), `test_execute_acks_late` (:827).
**Retrieve:**
```json
{"project":"ext-celery","query":"on_failure acks_late reject requeue WorkerLostError","limit":5,"detail":"ids"}
```
## Verdict
Adopt the whole matrix including the #4222 terminal-failure rule and the traceback-nulling hard-timeout path. Adapt broker primitives (basic.ack/basic.reject w/ requeue) and the WeakSet-based active-request tracking to your transport. Omit protocol-v1 branches and `_terminate_on_ack` deferral if you have no kill-on-accept feature.
