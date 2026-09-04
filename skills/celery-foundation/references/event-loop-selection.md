<!-- capsule-v2 -->
# Event loop selection & AMQP heartbeats — when does a worker use an event loop and who watches the broker socket?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How does the worker choose synloop vs asynloop, and how are protocol-level broker heartbeats driven without blocking task execution?

## should_use_eventloop + loops.asynloop/synloop
**Path/Symbol:** `celery/worker/worker.py:WorkController.should_use_eventloop` (:240-242); `celery/worker/consumer/consumer.py:__init__` loop choice (:236-238) + gevent timeout quirk (:243-247); `celery/worker/loops.py:asynloop` (:59-205), `synloop`, `_enable_amqheartbeats` (:29-45).
**Signature:** `should_use_eventloop() = detect_environment()=='default' and conninfo.transport.implements.asynchronous and not IS_WINDOWS`; `asynloop(obj, connection, consumer, blueprint, hub, qos, heartbeat, clock, hbrate=2.0)`.
**Data Shape:** `broker_heartbeat` (0=off), `broker_heartbeat_checkrate`; negotiated interval from `connection.get_heartbeat_interval()`; hub timer shared with ETA tasks.

### Decisive source
```python
# celery/worker/loops.py:29-45 — tick the broker heartbeat at 1/rate of interval
def _enable_amqheartbeats(timer, connection, rate=2.0):
    heartbeat_error = [None]
    if not connection:
        return heartbeat_error
    heartbeat = connection.get_heartbeat_interval()  # negotiated
    if not (heartbeat and connection.supports_heartbeats):
        return heartbeat_error

    def tick(rate):
        try:
            connection.heartbeat_check(rate)
        except Exception as e:
            # heartbeat_error is passed by reference can be updated
            # no append here list should be fixed size=1
            heartbeat_error[0] = e
    timer.call_repeatedly(heartbeat / rate, tick, (rate,))
    return heartbeat_error
```
```python
# celery/worker/loops.py:88-93 — pool startup gate inside asynloop
if not obj.restart_count and not obj.pool.did_start_ok():
    raise WorkerLostError('Could not start worker processes')
```

**Flow:** event-loop mode (prefork on POSIX with async transport): Evloop bootstep starts LAST, patches qos mutex to DummyLock (single-threaded hub), registers pool/result-handler fds, drains one prefetched event for clean state on amqp, then runs the poll loop calling `on_task_received` and periodically `heartbeat_check` — errors captured into the by-reference list instead of killing the loop. Thread mode (solo/threads/gevent or sync transports): synloop blocks in drain_events with computed timeouts; ack callbacks deferred via `_pending_operations` drained between iterations.
**Invariant:** (1) Broker heartbeat ticks must run even while idle — they're scheduled on the shared timer, never inline in message handling. (2) heartbeat_check errors are RECORDED not raised: the connection-errors machinery decides reconnect. (3) gevent has a known bug where a timed-out connect can NEVER retry (`consumer.__init__` sets `broker_connection_timeout=None` defensively). (4) did_start_ok only checked on first start (restart_count==0) because max-tasks-per-child corrupts later checks.
**Probe:** `t/unit/worker/test_loops.py::test_asynloop_*` pins loop entry/gates; `t/unit/worker/test_consumer.py::test_gevent_bug_disables_connection_timeout` (:72) pins the defensive quirk.
**Retrieve:**
```json
{"project":"ext-celery","query":"asynloop synloop _enable_amqheartbeats heartbeat_check","limit":5,"detail":"ids"}
```
## Verdict
Adopt: capability-based loop selection, shared-timer heartbeat ticking with error capture, and the first-start-only did_start_ok gate. Adapt kombu hub/polling and detect_environment to your runtime. Omit Windows gating if unsupported there.
