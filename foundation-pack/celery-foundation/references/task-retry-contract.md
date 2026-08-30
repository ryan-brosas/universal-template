<!-- capsule-v2 -->
# Task.retry contract — when is the retry-count check made relative to requeueing?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How does a bound task requeue itself with preserved routing, and what exactly happens when the retry budget is exhausted?

## Task.retry
**Path/Symbol:** `celery/app/task.py:Task.retry` (:767-861); signature reconstruction `Task.signature_from_request` (:760-779); default `max_retries = 3` (:241).
**Signature:** `retry(self, args=None, kwargs=None, exc=None, throw=True, eta=None, countdown=None, max_retries=None, **options)` raising `Retry` (normal operation) or `MaxRetriesExceededError`.
**Data Shape:** `request.retries` (int, 0-based attempt counter from message header), `request.called_directly`, `request.is_eager`, `delivery_info` (exchange/routing_key/priority carried from the current delivery).

### Decisive source
```python
# celery/app/task.py:830-861 — order matters: budget check BEFORE send
request = self.request
retries = request.retries + 1
if max_retries is not None:
    self.override_max_retries = max_retries
max_retries = self.max_retries if max_retries is None else max_retries
...
if not eta and countdown is None:
    countdown = self.default_retry_delay
is_eager = request.is_eager
S = self.signature_from_request(
    request, args, kwargs,
    countdown=countdown, eta=eta, retries=retries, **options)
if max_retries is not None and retries > max_retries:
    if exc:
        raise_with_context(exc)          # report the ORIGINAL failure
    raise self.MaxRetriesExceededError(...)
ret = Retry(exc=exc, when=eta or countdown, is_eager=is_eager, sig=S)
if is_eager:
    if throw: raise ret
    return ret
try:
    S.apply_async()
except Exception as exc:
    raise Reject(exc, requeue=False)     # broker refused → dead-letter
if throw:
    raise ret
return ret
```

**Flow:** compute next attempt number (`retries+1`) → optional per-call `max_retries` override stashed on `self.override_max_retries` → called-directly raises the original exception with context instead of queueing → default countdown only when neither eta nor countdown supplied → rebuild a Signature carrying `as_execution_options()` plus delivery_info (priority inherited; anon-exchange deliveries route by routing_key-as-queue) → **budget check `retries > max_retries` happens BEFORE any broker send**, so an exhausted task never requeues and then fails — it fails in place → eager mode returns/raises `Retry` for `apply()` to loop on → real send; send failure becomes `Reject(requeue=False)` so the poison message isn't looped.
**Invariant:** (1) The count check precedes requeueing. (2) Exhaustion surfaces the caller's `exc` (with context chain), not MaxRetriesExceededError, when one was provided. (3) Routing survives retries via `signature_from_request` replaying delivery_info — a porter who builds a fresh signature loses queue/priority. (4) `throw=False` turns retry into "best effort": the task continues running and its return value wins.
**Probe:** `t/unit/tasks/test_tasks.py::test_task_retries` family — `test_eager_retry_with_autoretry_for_exception` (:502-503) pins the eager Retry path; `test_autoretry_shared_retry_kwargs_not_mutated_by_max_retries_override` (:1788-1821) pins the override-not-propagating rule.
**Retrieve:**
```json
{"project":"ext-celery","query":"retry MaxRetriesExceededError signature_from_request","limit":5,"detail":"ids"}
```
## Verdict
Adopt: check-before-requeue ordering, original-exception-on-exhaustion, and delivery-info-based signature reconstruction. Adapt `override_max_retries` (a mutable attribute on a shared task object — thread-hostile) to per-attempt state. Omit protocol-v1 compat shims if your messages are all v2.
