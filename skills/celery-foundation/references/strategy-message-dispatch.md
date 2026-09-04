<!-- capsule-v2 -->
# Strategy message dispatch — from raw broker frame to pool handoff, what are the branches?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How is an incoming message normalized across protocol versions, screened for expiry/revocation, and routed through ETA/rate-limit gates to the pool?

## default strategy + create_task_handler
**Path/Symbol:** `celery/worker/strategy.py:default` (:88-209) returning `task_message_handler` (:145); receiver side `celery/worker/consumer/consumer.py:create_task_handler` (:741-786) with error handlers `on_unknown_message/on_unknown_task/on_invalid_task/on_decode_error`.
**Signature:** `strategy(message, body, ack, reject, callbacks)`; ack/reject arrive as PROMISES (`promise(call_soon_ack, (message.ack_log_error,), on_error=...)`) so the worker can chain prefetch restoration onto them.
**Data Shape:** v2: headers carry task/id/eta/expires/retries/timelimit; body `(args, kwargs, embed)` stays UNDECODED until the pool. v1/hybrid: full JSON payload converted via `proto1_to_proto2` / `hybrid_to_proto2`.

### Decisive source
```python
# celery/worker/strategy.py:145-209 — gate ladder after Req construction
if (req.expires or req.id in revoked_tasks) and req.revoked():
    return                                   # announce revoked, no execution
signals.task_received.send(sender=consumer, request=req)
...
if req.eta:
    try:
        eta = to_timestamp(to_system_tz(req.eta)) if req.utc \
              else to_timestamp(req.eta, app.timezone)
    except (OverflowError, ValueError) as exc:
        error("Couldn't convert ETA %r ...", ...)
        req.reject(requeue=False)            # poison eta → drop
if rate_limits_enabled:
    bucket = get_bucket(task.name)
if eta and bucket:
    consumer.qos.increment_eventually()
    return call_at(eta, limit_post_eta, (req, bucket, 1), priority=6)
if eta:
    consumer.qos.increment_eventually()
    call_at(eta, apply_eta_task, (req,), priority=6)
    return task_message_handler
if bucket:
    return limit_task(req, bucket, 1)
task_reserved(req)
handle(req)                                   # → semaphore → pool
```
```python
# celery/worker/consumer/consumer.py:750-786 — protocol dispatch ladder
try:
    type_ = message.headers['task']           # v2
except TypeError:
    return on_unknown_message(None, message)
except KeyError:
    payload = message.decode()
    type_, payload = payload['task'], payload  # v1
try:
    strategy = strategies[type_]
except KeyError as exc:
    return on_unknown_task(None, message, exc) # reject + mark_as_failure(NotRegistered)
```

**Flow:** handler resolves protocol version → strategy builds a Request (`Req`) via `create_request_cls` (per-task optimized class) → expiry/revocation screen (revoked_tasks LimitedSet + stamped-header revokes) → received signal + optional task-received event → ETA branch converts to epoch seconds for `timer.call_at(..., priority=6)` with qos.increment_eventually holding the slot until fire → rate-limit branch enters TokenBucket which requeues-to-head preserving order when out of tokens → else reserve and hand to `on_task_request` (semaphore-bounded).
**Invariant:** (1) Unknown task ids are REJECTED (not acked) AND marked FAILURE in backend so callers unblock — a porter who only rejects leaves results pending forever. (2) Decode errors ACK immediately (`on_decode_error` → message.ack) to avoid redelivery loops on permanently corrupt payloads. (3) qos increment happens BEFORE timer arming; `apply_eta_task` decrements when firing. (4) The returned `task_message_handler` from the eta branch keeps kombu's drain loop contract (callback returning itself = keep consuming).
**Probe:** `t/unit/worker/test_strategy.py` pins the gate ladder (24 tests incl. eta/bucket branches); `t/unit/worker/test_consumer.py::test_on_decode_error_*` family pins immediate-ack.
**Retrieve:**
```json
{"project":"ext-celery","query":"task_message_handler apply_eta_task limit_task bucket","limit":5,"detail":"ids"}
```
## Verdict
Adopt the ladder order (protocol → registry → expiry/revoked → ETA → rate-limit → reserve) and both poison-message policies (reject+mark vs ack). Adapt kombu promise plumbing and TokenBucket timing to your loop. Omit proto1/hybrid conversion if you only speak one protocol.
