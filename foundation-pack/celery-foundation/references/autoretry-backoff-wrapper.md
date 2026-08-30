<!-- capsule-v2 -->
# Autoretry backoff wrapper — how do you add retry to any task without editing its body?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How is automatic retry layered onto a task's run function, and which exceptions must pass through untouched?

## add_autoretry_behaviour
**Path/Symbol:** `celery/app/autoretry.py:add_autoretry_behaviour` (:11-120); backoff formula `celery/utils/time.py:get_exponential_backoff_interval` (:463-477).
**Signature:** `add_autoretry_behaviour(task, **options)` reading `autoretry_for`, `dont_autoretry_for`, `retry_kwargs`, `retry_backoff` (float, False=off), `retry_backoff_max` (default 600), `retry_jitter` (default True); swaps `task._orig_run, task.run = task.run, run`.
**Data Shape:** The wrapper closes over the exception tuples and retry config; per-attempt state comes from `task.request.retries`; countdown is an int seconds value (jitter range `[0, computed]`).

### Decisive source
```python
# celery/app/autoretry.py:31-58 — pass-through ladder then backoff
@wraps(task.run)
def run(*args, **kwargs):
    try:
        return task._orig_run(*args, **kwargs)
    except Ignore:
        raise                    # Ignore never retried, even if listed
    except Retry:
        raise                    # manual retries inside body win
    except dont_autoretry_for:
        raise                    # explicit blacklist beats whitelist
    except autoretry_for as exc:
        retry_kwargs_for_attempt = retry_kwargs.copy()
        if retry_backoff:
            retry_kwargs_for_attempt['countdown'] = \
                get_exponential_backoff_interval(
                    factor=int(max(1.0, retry_backoff)),
                    retries=task.request.retries,
                    maximum=retry_backoff_max,
                    full_jitter=retry_jitter)
        ...
        ret = task.retry(exc=exc, **retry_kwargs_for_attempt)
        raise ret
```
```python
# celery/utils/time.py:471-477 — full jitter
countdown = min(maximum, factor * (2 ** retries))
if full_jitter:
    countdown = random.randrange(countdown + 1)
return max(0, countdown)
```

**Flow:** decorator installs once (guard: only when `autoretry_for and not hasattr(task, '_orig_run')`) → each call runs the original body → matching exceptions get a fresh kwargs dict with a jittered exponential countdown derived from the CURRENT attempt number → delegates to `Task.retry` (so budget checks, routing preservation, and exhaustion behavior are inherited from the retry contract capsule) → cleanup of `override_max_retries` attr after each attempt.
**Invariant:** (1) `Ignore` and `Retry` are caught BEFORE the whitelist — control-flow exceptions from inside the task must not be swallowed into a retry loop. (2) `dont_autoretry_for` is checked before `autoretry_for`. (3) `retry_kwargs` is copied PER ATTEMPT (`retry_kwargs_for_attempt`) — mutating shared dicts across retries was CVE-grade bug #6181; tests pin that base-class dicts are never mutated. (4) Backoff factor coerced via `int(max(1.0, retry_backoff))` so fractional backoff ≥ 1s.
**Probe:** `t/unit/tasks/test_tasks.py::test_autoretry_does_not_mutate_shared_base_class_retry_kwargs` (:836-879) pins non-mutation; `test_eager_retry_with_autoretry_for_exception` (:502-503) pins eager-mode integration.
**Retrieve:**
```json
{"project":"ext-celery","query":"add_autoretry_behaviour autoretry_for retry_backoff","limit":5,"detail":"ids"}
```
## Verdict
Adopt the pass-through ladder order (Ignore → Retry → blacklist → whitelist), the copy-per-attempt rule, and the exact jitter formula. Adapt config plumbing (decorator options vs attributes) to your framework's task-registration style. Omit the `_orig_run` attribute sentinel in favor of a WeakSet if your tasks are unpicklable wrappers.
