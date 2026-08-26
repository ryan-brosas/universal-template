<!-- capsule-v2 -->
# Redis backend retry policy — how do backend writes survive transient connection loss?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How is a retry policy merged, applied to every KV operation, and what does the write path look like (including the pub/sub fan-out)?

## RedisBackend.ensure + retry_policy + _set
**Path/Symbol:** `celery/backends/redis.py:RedisBackend.retry_policy` (:494-500), `ensure` (:512-518), `on_connection_error` (:520-525), `set/_set` (:527-540), `exception_safe_to_retry` (:488); base-class twin `_ensure_retryable` in `celery/backends/base.py` (:636-672) with `get_exponential_backoff_interval`; E_LOST template :72.
**Signature:** `ensure(fun, args, **policy)` wrapping kombu `retry_over_time(fun, self.connection_errors, args, {}, errback, **retry_policy)`; default policy from `task_publish_retry_policy`: `{max_retries: 3, interval_start: 0, interval_max: 1, interval_step: 0.2}` (celery/app/defaults.py:303-309).
**Data Shape:** `_transport_options['retry_policy']` overrides base keys per-key; value size guarded by `_MAX_STR_VALUE_SIZE` raising BackendStoreError; chord counter key `<group>.t`.

### Decisive source
```python
# celery/backends/redis.py:512-540 — wrap every op, log-and-wait between tries
def ensure(self, fun, args, **policy):
    retry_policy = dict(self.retry_policy, **policy)
    max_retries = retry_policy.get('max_retries')
    return retry_over_time(
        fun, self.connection_errors, args, {},
        partial(self.on_connection_error, max_retries),
        **retry_policy)

def on_connection_error(self, max_retries, exc, intervals, retries):
    tts = next(intervals)
    logger.error(E_LOST.strip(), retries, max_retries or 'Inf',
                 humanize_seconds(tts, 'in '))
    return tts                                   # sleep hint for retry_over_time

def set(self, key, value, **retry_policy):
    if isinstance(value, str) and len(value) > self._MAX_STR_VALUE_SIZE:
        raise BackendStoreError('value too large for Redis backend')
    return self.ensure(self._set, (key, value), **retry_policy)

def _set(self, key, value):
    with self.client.pipeline() as pipe:
        if self.expires:
            pipe.setex(key, self.expires, value)
        else:
            pipe.set(key, value)
        pipe.publish(key, value)                 # wake pub/sub result waiters
        pipe.execute()
```

**Flow:** every public KV op (get/mset/set/store_result path) funnels through `ensure` → kombu retry_over_time catches ONLY `connection_errors`, calls the errback which logs `E_LOST ("Connection to Redis lost: Retry (n/max) in Xs")` and returns the next interval → exhausted retries re-raise. The base class offers an alternative ladder (`_ensure_retryable`) driven by `always_retry` config using full-jitter exponential backoff in ms with a fallback exception wrapper — two generations of the same idea coexisting.
**Invariant:** (1) The SET+PUBLISH pairing must be atomic-in-one-pipeline: without the publish, AsyncResult.waiters subscribed on the channel never wake. (2) Only CONNECTION errors are retried — application errors (wrong types) must fail fast; `exception_safe_to_retry` gates the always_retry ladder identically. (3) The errback RETURNS the interval (kombu contract), it doesn't sleep itself. (4) Value-size check happens BEFORE any network I/O.
**Probe:** `t/unit/backends/test_redis.py::test_ensure_policies_eager_*`/`test_on_connection_error` family (106 tests) pin policy merge and E_LOST logging; `t/unit/backends/test_base.py::test_store_result_retries` style tests pin the base ladder.
**Retrieve:**
```json
{"project":"ext-celery","query":"RedisBackend ensure retry_policy on_connection_error","limit":5,"detail":"ids"}
```
## Verdict
Adopt: single-funnel op wrapper, connection-errors-only filter, log-with-next-interval errback, pipeline(set+publish). Adapt retry_over_time and redis-py pipeline to your client. Omit the legacy `_ensure_retryable` ladder if you standardize on one mechanism — porting both invites drift.
