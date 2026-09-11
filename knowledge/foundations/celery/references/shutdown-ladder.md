<!-- capsule-v2 -->
# Shutdown ladder — what is the exact difference between warm stop, cold terminate, and soft shutdown?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What happens on SIGTERM vs SIGQUIT vs expiry of the soft-shutdown window, and in what order do components drain?

## WorkController.stop/terminate/_shutdown + cancel_active_requests
**Path/Symbol:** `celery/worker/worker.py:WorkController.stop` (:296), `terminate` (:305), `_shutdown` (:312-320) with `default_socket_timeout(SHUTDOWN_SOCKET_TIMEOUT=5.0)` (#975), `wait_for_soft_shutdown` (:421-441); consumer side `cancel_active_requests` (consumer.py:809-838); blueprint reverse-order teardown from bootsteps capsule.
**Signature:** `stop(in_sighandler=False, exitcode=None)` warm; `terminate(in_sighandler=False)` cold; `blueprint.stop(parent, terminate=not warm); blueprint.join()`; signal handlers in celery/apps/worker.py set `state.should_stop/should_terminate`.
**Data Shape:** config knobs: `worker_soft_shutdown_timeout` (+`worker_enable_soft_shutdown_on_idle`), pool flag `signal_safe` deciding whether stop runs INSIDE a signal handler.

### Decisive source
```python
# celery/worker/consumer/consumer.py:815-837 — which tasks may be cancelled on drain
def should_cancel(request):
    if not request.task.acks_late:
        return True                    # early-ack: broker copy gone → finish-or-die
    if not request.acknowledged:
        if request.id in successful_requests:
            return False               # succeeded but unacked: let it ack
        return True                    # unacked late task: redeliver via broker
    return False                       # already acked: must run to completion
...
for request in requests_to_cancel:
    # For acks_late tasks, don't emit RETRY signal since broker will
    # handle redelivery. For non-acks_late, emit RETRY as usual.
    emit_retry = not request.task.acks_late
    request.cancel(self.pool, emit_retry=emit_retry)
```

**Flow:** warm stop: close consumer (stops fetching) → blueprint.close+stop in REVERSE step order under a 5s socket timeout so dead sockets can't hang teardown → join greenlets; cold terminate: same but steps get `.terminate()`. Soft shutdown (opt-in): on TERM, wait up to `worker_soft_shutdown_timeout` while active tasks finish (skipped when idle unless forced) before entering cold path — lets short tasks complete and long tasks be requeued by another worker. During drain, `cancel_active_requests` applies the should_cancel matrix with the emit_retry asymmetry.
**Invariant:** (1) The socket-timeout wrapper exists because blueprint.stop performs broker I/O (#975). (2) A successful-but-unacked task must NOT be cancelled or its result is lost after the ack was sent. (3) emit_retry flips on acks_late: late tasks rely on broker redelivery instead of fabricating RETRY states. (4) `maybe_shutdown()` checkpoints raise WorkerShutdown/Terminate inside loops — nothing polls flags from one central place.
**Probe:** `t/unit/worker/test_worker.py::test_shutdown_*`/soft-shutdown tests pin stop/terminate ordering; `t/unit/worker/test_consumer.py::test_cancel_active_requests_success_should_not_be_canceled` pins the matrix.
**Retrieve:**
```json
{"project":"ext-celery","query":"cancel_active_requests should_cancel soft shutdown","limit":5,"detail":"ids"}
```
## Verdict
Adopt: close-consumer-first ordering, bounded-teardown timeout, the three-way cancellation matrix, and opt-in soft-drain window. Adapt signal plumbing (should_stop flags) to your supervisor integration. Omit Windows-specific branches (`IS_WINDOWS` eventloop gating).
