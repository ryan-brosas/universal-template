<!-- capsule-v2 -->
# Dedup on redelivery — how do you safely skip a task that already succeeded?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** When acks_late + dedup are enabled and a message is redelivered, how does the worker prove prior success AND repair missing side effects without double-running callbacks?

## trace_task dedup short-circuit
**Path/Symbol:** `celery/app/trace.py:build_tracer` dedup block (:505-562); helper `_dispatch_callbacks_and_chain` (:426-473); in-process set from `celery/worker/state.successful_requests`; gating flags computed at :369-371.
**Signature:** gate: `deduplicate_successful_tasks = ((app.conf.task_acks_late or task.acks_late) and app.conf.worker_deduplicate_successful_tasks and app.backend.persistent)`; check order: in-process set → backend meta state.
**Data Shape:** requires extended result metadata persisted (`result_extended=True`) because children/callback-repair reads `_meta['children']` and `_meta['result']`.

### Decisive source
```python
# celery/app/trace.py:511-548 — two-tier proof then idempotent repair
if task_request.id in successful_requests:
    return trace_ok_t(R, I, T, Rstr)          # tier 1: this worker saw it
r = AsyncResult(task_request.id, app=app)
try:
    state = r.state
except BackendGetMetaError:
    pass                                       # unknown → run it (fail open)
else:
    if state == SUCCESS:
        info(LOG_IGNORED, {...'Task already completed successfully.'})
        try:
            _meta = r._get_task_meta()
            stored_retval = _meta.get('result')
            # Children are populated by mark_as_done on the original
            # execution. If present, callbacks were already dispatched.
            _children = _meta.get('children')
            if (_callbacks or _chain) and not _children:
                _dispatch_callbacks_and_chain(stored_retval, ...)
            successful_requests.add(task_request.id)
        except MemoryError:
            raise
        except Exception as exc:
            # Permanent failures will requeue indefinitely. Broker-level
            # dead-letter / max-delivery-count policies are the intended
            # circuit-breaker.
            logger.error('Failed to dispatch chain/callbacks ...', exc_info=True)
            raise Reject(exc, requeue=True)
```

**Flow:** only redelivered messages enter the check (`delivery_info.redelivered`) → tier 1: local bounded set (fast path, same-worker retries) → tier 2: backend meta read; BackendGetMetaError fails OPEN (run the task — better duplicate than loss) → on proven success: skip execution, re-dispatch callbacks/chain ONLY when metadata shows no children (i.e. original died between dispatching work and recording it), cache id locally → repair failures raise Reject(requeue=True), deliberately relying on broker DLQ/max-delivery as the circuit breaker rather than dropping.
**Invariant:** (1) Fail-open on backend read errors — availability over exactly-once. (2) Callback repair is guarded by the `children` marker so repaired tasks don't double-fire link callbacks that DID succeed. (3) The requeue-on-repair-failure path REQUIRES broker-side poison-message controls; the comment says so explicitly. (4) The feature is gated on acks_late — with early acks the broker already guarantees no redelivery of succeeded tasks.
**Probe:** `t/unit/tasks/test_trace.py::test_trace_dedup_*` family within 66 tests pins skip/repair/fail-open branches; integration via `t/unit/tasks/test_tasks.py` eager twins.
**Retrieve:**
```json
{"project":"ext-celery","query":"deduplicate_successful_tasks redelivered successful_requests","limit":5,"detail":"ids"}
```
## Verdict
Adopt the two-tier proof, fail-open posture, children-marker repair guard, and DLQ-as-breaker rule. Adapt the persistent-metadata requirement to your result store (any store keeping children+result works). Omit entirely if you can't tolerate duplicates another way — this is opt-in complexity.
