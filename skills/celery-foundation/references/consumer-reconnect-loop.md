<!-- capsule-v2 -->
# Consumer reconnect loop — how does a worker survive broker loss without hot-spinning or leaking prefetch?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What is the restart policy around `blueprint.start`, and what must be cleaned up / re-snapshotted on every reconnect?

## Consumer.start + on_connection_error_after_connected
**Path/Symbol:** `celery/worker/consumer/consumer.py:Consumer.start` (:352-405), `on_close` (:646), `on_connection_error_after_connected` (:420-503), `ensure_connected` (:564-620); rate limiter `billiard.common.restart_state(maxR=5, maxT=1)`.
**Signature:** loop condition `while blueprint.state not in {CLOSE, TERMINATE}`; recoverable error set = `connection_errors (+ channel_errors if app.conf.broker_channel_error_retry)`.
**Data Shape:** Consumer tracks `restart_count` (first start counts as a restart), `first_connection_attempt`, `broker_connection_retry_attempt`, prefetch state: `initial_prefetch_count`, `max_prefetch_count = pool.num_processes * prefetch_multiplier`, `_maximum_prefetch_restored`, and QoS mode flag `qos_global` (None/True/False).

### Decisive source
```python
# celery/worker/consumer/consumer.py:362-404 — the outermost retry loop
try:
    blueprint.start(self)
except recoverable_errors as exc:
    ...
    connection_retry = self.app.conf[connection_retry_type]
    if not connection_retry:
        raise WorkerShutdown(1) from exc          # no-retry config → clean exit
    if isinstance(exc, OSError) and exc.errno == errno.EMFILE:
        raise WorkerTerminate(1) from exc         # fd exhaustion → abort hard
    maybe_shutdown()
    if blueprint.state not in STOP_CONDITIONS:
        if self.connection:
            self.on_connection_error_after_connected(exc)
        else:
            self.on_connection_error_before_connected(exc)
        self.on_close()
        blueprint.restart(self)
```
```python
# :424-441 — cleanup must not hang on a dead socket (#9705)
self.connection.collect(socket_timeout=COLLECT_SOCKET_TIMEOUT)  # 5.0s
connection, self.connection = self.connection, None
if connection:
    ignore_errors(connection, connection.close)
```

**Flow:** each iteration checks shutdown flags → throttles via `restart_state.step()` (billiard raises RestartFreqExceeded > 5 restarts/1s → sleep(1)) → full blueprint start; on recoverable error classify (startup vs post-connect, EMFILE special case) → after-connected path: collect-with-timeout the broken connection, close it HERE (not in Connection.stop — graceful shutdown needs the connection open for in-flight acks), optionally cancel active acks_late requests gated by `worker_cancel_long_running_tasks_on_connection_loss`, then snapshot prefetch reduction: `initial_prefetch_count = max(prefetch_multiplier, max_prefetch - active_count*multiplier)` unless per-consumer QoS (`qos_global is False`, quorum queues #9512) where reduction is skipped entirely → blueprint.restart rebuilds steps.
**Invariant:** (1) Restart frequency is bounded BEFORE reconnecting — unbounded loops melt brokers. (2) Broken-connection cleanup carries an explicit socket timeout or the worker hangs inside channel close forever. (3) Prefetch restoration is LAZY: the first ack/reject promise after restart triggers `_restore_prefetch_count_after_connection_restart` which re-raises qos under `self.qos._mutex`. (4) Per-consumer QoS mode must reset to maximum instead of reducing, else the worker stays stuck at reduced throughput. (5) `on_close()` also re-syncs `reserved_requests := tuple(active_requests)` and clears bucket pending queues.
**Probe:** `t/unit/worker/test_consumer.py::test_max_restarts_exceeded` (:373), `test_do_not_restart_when_closed` (:387), `test_restore_prefetch_count_on_restart` (:113), `test_prefetch_count_reduction_respects_qos_global` (:163).
**Retrieve:**
```json
{"project":"ext-celery","query":"Consumer.start blueprint.restart recoverable_errors EMFILE","limit":5,"detail":"ids"}
```
## Verdict
Adopt the loop skeleton: throttle → start → classify error → timeout-guarded cleanup → snapshot → restart. Adapt kombu ensure_connection/failover semantics and billiard restart_state to your transport. Omit quorum-queue QoS branches only if you have no per-consumer QoS transports.
