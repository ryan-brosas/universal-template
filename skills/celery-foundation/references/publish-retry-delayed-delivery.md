<!-- capsule-v2 -->
# Publish-side retry policy & delayed delivery routing — how does a producer survive broker flaps and route ETA tasks natively?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What retries protect task PUBLISH, and how are countdown/eta tasks routed to native delayed-delivery exchanges on quorum queues?

## send_task_message + send_task quorum branch
**Path/Symbol:** `celery/app/amqp.py:send_task_message` (:506-593) with defaults `_create_task_message` factory (:485-504); `celery/app/base.py:Celery.send_task` (:846-1041) delayed-delivery branch :934-966 and expires normalization :968-992; bootstep `celery/worker/consumer/delayed_delivery.py:DelayedDelivery` (requires=(Tasks,), include_if=detect_quorum_queues).
**Signature:** `send_task_message(producer, name, message, exchange=None, routing_key=None, queue=None, retry=None, retry_policy=None, ...)`; kombu `retry_over_time` semantics; `calculate_routing_key(countdown_seconds, routing_key)` from kombu.native_delayed_delivery.
**Data Shape:** default publish policy `{max_retries: 3, interval_start: 0, interval_max: 1, interval_step: 0.2}`; anon-exchange conversion rule `(not exchange or not routing_key) and exchange_type == 'direct' → exchange='', routing_key=qname`.

### Decisive source
```python
# celery/app/base.py:943-958 — eta/countdown → delayed-exchange routing key
if exchange_type != 'direct':
    if eta:
        ...
        countdown = (maybe_make_aware(eta) - self.now()).total_seconds()
    if countdown:
        if countdown > 0:
            routing_key = calculate_routing_key(int(countdown), routing_key)
            exchange = Exchange('celery_delayed_27', type='topic')
            options.pop("queue", None)
            options['routing_key'] = routing_key
            options['exchange'] = exchange
else:
    logger.warning('Direct exchanges are not supported with native
                   delayed delivery...')   # falls back to worker-side ETA timer
```
```python
# celery/worker/consumer/delayed_delivery.py:88-101 — per-URL setup with bounded retry
for broker_url in broker_urls:
    try:
        retry_over_time(self._setup_delayed_delivery, args=(c, broker_url),
                        catch=RETRIED_EXCEPTIONS, errback=self._on_retry,
                        interval_start=RETRY_INTERVAL, max_retries=MAX_RETRIES)
    except Exception as e:
        setup_errors.append((broker_url, e))     # partial failure tolerated
if len(setup_errors) == len(broker_urls):
    logger.critical("Failed to setup delayed delivery for ALL broker URLs.")
```

**Flow:** publish path merges default+custom retry policy into `_rp`, converts direct-with-no-routing to anon exchange, declares the target queue unless Broadcast, then `producer.publish(..., retry=retry, retry_policy=_rp)` — kombu re-publishes on connection loss up to 3 times with stepped intervals. Worker side, DelayedDelivery bootstep activates ONLY when quorum queues detected (`include_if`), declaring the delay ladder exchanges (delays 1..2^27s via celery_delayed_N topics) per broker URL with 3 bounded retries per URL, tolerating individual-URL failures but logging critical when ALL fail. Expires in the past is clamped to 0 with an explicit warning citing RabbitMQ TTL-0 semantics.
**Invariant:** (1) Publish-retry protects the PRODUCER side only — combined with consumer acks this yields at-least-once end-to-end. (2) Direct exchanges cannot do native delayed delivery; behavior degrades to worker-side ETA timers holding prefetch slots (the warning explains the stall hazard). (3) Queue option must be POPPED when rerouting or the message double-routes. (4) Broadcast queues skip declare.
**Probe:** `t/unit/worker/test_native_delayed_delivery.py` pins include_if/retry/validation (queue-type whitelist {classic, quorum}); `t/unit/app/test_amqp.py::test_send_task_message_*` pins policy merge and anon-exchange conversion.
**Retrieve:**
```json
{"project":"ext-celery","query":"send_task_message retry_policy calculate_routing_key DelayedDelivery","limit":5,"detail":"ids"}
```
## Verdict
Adopt: merged-policy publish retry, anon-exchange conversion, expires clamp-to-zero, per-URL bounded setup retries. Adapt kombu publish and RabbitMQ delayed-exchange conventions to your broker. Omit native delayed delivery entirely if your broker lacks topic-ladder support — worker-side ETA timers are the portable fallback.
