<!-- capsule-v2 -->
# Rate limiter token bucket — how do you throttle a task type without blocking workers?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How are per-task rate limits enforced while preserving message order, and how does the ETA timer interplay with the bucket?

## Consumer._schedule_bucket_request + TokenBucket
**Path/Symbol:** `celery/worker/consumer/consumer.py:_schedule_bucket_request` (:322-341), `_limit_task` (:342), `_limit_post_eta` (:345), `bucket_for_task` (:315); primitive `kombu.utils.limits.TokenBucket`; buckets dict `task_buckets = defaultdict(lambda: None)` reset from task.rate_limit attrs.
**Signature:** `bucket.add((request, tokens)); bucket.pop() -> (request, tokens) (IndexError when empty); bucket.can_consume(tokens) -> bool; bucket.expected_time(tokens) -> seconds`; scheduling via `timer.call_after(hold, self._schedule_bucket_request, (bucket,), priority=pri)` with rotating priority `self._limit_order = (self._limit_order + 1) % 10`.
**Data Shape:** rate strings like `"5/s"|"5/m"|"5/h"` parsed by `celery/utils/time.rate` into TokenBucket capacity=1; disabled per worker via `worker_disable_rate_limits`.

### Decisive source
```python
# celery/worker/consumer/consumer.py:322-341 — drain-then-hold loop
def _schedule_bucket_request(self, bucket):
    while True:
        try:
            request, tokens = bucket.pop()
        except IndexError:
            break                                   # empty: done
        if bucket.can_consume(tokens):
            self._limit_move_to_pool(request)       # under limit → execute now
            continue
        else:
            # requeue to head, keep the order.
            bucket.contents.appendleft((request, tokens))
            pri = self._limit_order = (self._limit_order + 1) % 10
            hold = bucket.expected_time(tokens)
            self.timer.call_after(
                hold, self._schedule_bucket_request, (bucket,), priority=pri)
            break
```

**Flow:** strategy hands each request to its task's bucket (or straight to pool if none) → requests queue in FIFO inside the bucket → drain loop consumes while tokens allow → on first refusal the request goes back to the HEAD (order preserved) and a timer re-runs the scheduler after expected_time; rotating priorities prevent timer starvation. The eta+bucket combination (`_limit_post_eta`) decrements qos immediately then holds the request in-bucket until BOTH conditions clear.
**Invariant:** (1) Requeue-to-head is what makes the limit FAIR — appending would invert order under throttling. (2) Throttled tasks hold their prefetch slot (qos incremented on receipt): a too-low rate limit can deadlock throughput by prefetch exhaustion — operators must size prefetch accordingly. (3) Buckets live in a defaultdict returning None so disabled/absent limits short-circuit. (4) `on_close()` clears bucket pending queues on connection loss so held requests aren't orphaned.
**Probe:** `t/unit/worker/test_consumer.py::test_schedule_bucket_requests_*` family within 97 tests pins head-requeue and drain semantics; kombu-side TokenBucket covered upstream.
**Retrieve:**
```json
{"project":"ext-celery","query":"_schedule_bucket_request bucket_for_task can_consume","limit":5,"detail":"ids"}
```
## Verdict
Adopt: FIFO-in-bucket with head requeue, expected-time rescheduling with rotating priorities, and the eta+rate combined path. Adapt kombu TokenBucket/timer priorities to your loop. Omit remote rate-limit control commands if limits are static config.
