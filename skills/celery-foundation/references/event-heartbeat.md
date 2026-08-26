<!-- capsule-v2 -->
# Event heartbeat — how does a worker broadcast liveness with metrics?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How are worker-heartbeat events scheduled, coupled to the events subsystem, and what payload must they carry?

## Heart (service) + Heart (bootstep)
**Path/Symbol:** `celery/worker/heartbeat.py:Heart` (:14-61); bootstep wrapper `celery/worker/consumer/heart.py:Heart` (requires=(Events,), enabled=not without_heartbeat); distinct from AMQP protocol heartbeats (`celery/worker/loops.py:_enable_amqheartbeats`).
**Signature:** `Heart(timer, eventer, interval=None)` default interval 2.0s; `start()` sends `worker-online` then `timer.call_repeatedly(interval, self._send, ('worker-heartbeat',))`; `stop()` cancels tref and sends `worker-offline` once (retry=False).
**Data Shape:** heartbeat event payload: `freq=interval`, `active=len(active_requests)`, `processed=all_total_count[0]`, `loadavg=load_average()`, plus `SOFTWARE_INFO` (sys/platform versions).

### Decisive source
```python
# celery/worker/heartbeat.py:33-47 — lifecycle coupling to the dispatcher
self.eventer.on_enabled.add(self.start)
self.eventer.on_disabled.add(self.stop)
# Only send heartbeat_sent signal if it has receivers.
self._send_sent_signal = (
    heartbeat_sent.send if heartbeat_sent.receivers else None)

def _send(self, event, retry=True):
    if self._send_sent_signal is not None:
        self._send_sent_signal(sender=self)
    return self.eventer.send(event, freq=self.interval,
                             active=len(active_requests),
                             processed=all_total_count[0],
                             loadavg=load_average(),
                             retry=retry,
                             **SOFTWARE_INFO)
```

**Flow:** bootstep creates service after Events step → start gated on `eventer.enabled`: if events are disabled at startup NO timer runs; enabling events later fires `on_enabled` → heart starts mid-run; disabling stops it and emits a final offline event → each tick publishes worker-heartbeat through the event dispatcher (buffered/flushed by hub) carrying live gauges.
**Invariant:** (1) The heartbeat is EVENT-plane liveness only — brokers don't see it; AMQP heartbeat_check is a separate mechanism in loops.py. (2) `heartbeat_sent` signal object is resolved AT CONSTRUCTION to avoid per-tick receiver checks — a porter calling `.send()` unconditionally pays signal dispatch cost every 2s. (3) stop() is idempotent via tref None-check. (4) Gossip consumes these same events for node-loss detection — changing payload keys breaks cluster monitoring.
**Probe:** `t/unit/worker/test_heartbeat.py::test_start_stop` (:42), `test_send_sends_signal` (:52), `test_start_when_disabled` (:60), `test_stop_when_disabled` (:69), `test_message_retries` (:77).
**Retrieve:**
```json
{"project":"ext-celery","query":"Heart worker-heartbeat call_repeatedly eventer","limit":5,"detail":"ids"}
```
## Verdict
Adopt: online/tick/offline triple, enabled/disabled coupling so heartbeats track the events subsystem, gauge-bearing payload. Adapt kombu Timer.call_repeatedly and event dispatcher buffering to your loop. Omit retry semantics on send if your transport is reliable in-process.
