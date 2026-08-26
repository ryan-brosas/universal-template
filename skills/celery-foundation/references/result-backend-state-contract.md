<!-- capsule-v2 -->
# Result backend state contract — what does store_result guarantee and how do states map to caller semantics?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What is the minimal write API of a result backend, which states are stored for which transitions, and how are exceptions made storable?

## BaseBackend.store_result / encode_result / _get_result_meta
**Path/Symbol:** `celery/backends/base.py:Backend.store_result` (:674-700), `encode_result`, `_get_result_meta` (:582+), `exception_safe_to_retry`/`always_retry` ladder (:636-672), `mark_as_*` family (:181-330); KeyValueStoreBackend (:900+) key scheme `task_keyprefix + task_id`.
**Signature:** `store_result(task_id, result, state, traceback=None, request=None, **kwargs)` → `encode_result(result, state)` → `_store_result`; meta dict carries `{status, result, traceback, children, date_done, date_killed?}`.
**Data Shape:** states: PENDING (default/unknown), STARTED (only when track_started), RETRY, FAILURE, SUCCESS, REVOKED, IGNORED; PROPAGATE_STATES = {FAILURE, REVOKED} — only these re-raise on `.get()`.

### Decisive source
```python
# celery/backends/base.py:674-692 — every write funnels here
def store_result(self, task_id, result, state,
                 traceback=None, request=None, **kwargs):
    """Update task state and result.

    if always_retry_backend_operation is activated, in the event of a
    recoverable exception, then retry operation with an exponential
    backoff until a limit has been reached.
    """
    result = self.encode_result(result, state)      # exc → picklable form
    kwargs.update({'task_id': task_id, 'state': state})
    self._ensure_retryable(
        self._store_result,
        fallback_exc=BackendStoreError,
        fallback_msg="failed to store result on the backend",
        result=result, ...)
```
```python
# :189-198 — failure marks chord participation too
def mark_as_failure(self, task_id, exc, traceback=None, request=None,
                    store_result=True, call_errbacks=True, state=FAILURE):
    if store_result:
        self.store_result(task_id, exc, state, traceback=traceback,
                          request=request)
    if request:
        if request.chord:
            self.on_chord_part_return(request, state, exc)
```

**Flow:** trace calls mark_as_done/mark_as_failure/mark_as_retry/mark_as_revoked → each stores via store_result (encode makes exceptions picklable via get_pickleable_exception, creates dynamic exception CLASSES for foreign types) then performs canvas duties. IGNORED state records deliberately-skipped tasks so callers see terminality rather than eternal PENDING. The DisabledBackend sentinel keeps ignore-result apps honest by raising on access.
**Invariant:** (1) PENDING means "no record", not "queued" — backends must never fabricate it. (2) Only PROPAGATE_STATES propagate to `.get()`; RETRY/SUCCESS/IGNORED don't. (3) Exception pickling must never fail the store: unknown exception types degrade to dynamically-created subclasses of the configured exception class. (4) Writes are idempotent per (task_id, state-transition) — retries may double-write.
**Probe:** `t/unit/backends/test_base.py::test_store_result_*`/`test_encode_result_*` within 128 tests; `t/unit/backends/test_redis.py::test_on_message_call_to_deletes_eager_result` style integration for pub/sub wake.
**Retrieve:**
```json
{"project":"ext-celery","query":"BaseBackend store_result encode_result _get_result_meta","limit":5,"detail":"ids"}
```
## Verdict
Adopt: single-funnel store with encoded results, the state taxonomy with PROPAGATE_STATES gating, exception-class fabrication, and idempotent writes. Adapt KV layout and TTL handling to your store. Omit sync/async result-consumption machinery (asynchronous.py Drainer) unless you implement blocking `.get()`.
