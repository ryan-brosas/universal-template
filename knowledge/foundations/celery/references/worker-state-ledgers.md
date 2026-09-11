<!-- capsule-v2 -->
# Worker state ledgers — what shared mutable state do all worker components read and write?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** Where does the worker track in-flight tasks, successful ids, revokes, and shutdown intent — and what are the exact lifecycle hooks?

## celery.worker.state
**Path/Symbol:** `celery/worker/state.py` module globals: `requests = {}` (:49), `reserved_requests = WeakSet()` (:52), `active_requests = WeakSet()` (:55), `successful_requests = LimitedSet(maxlen=SUCCESSFUL_MAX, expires=SUCCESSFUL_EXPIRES)` (:58), `revoked = LimitedSet(maxlen=REVOKES_MAX, expires=REVOKE_EXPIRES)` (:68), flags `should_stop/should_terminate` (:73-74); hooks `task_reserved` (:96), `task_accepted` (:104), `task_ready` (:118), `maybe_shutdown` (:88).
**Signature:** `task_reserved(request)` → requests[id]=request + reserved.add; `task_accepted(request)` → requests[id]=request + active.add + counters; `task_ready(request, successful=False)` → optional successful_requests.add + pop/discard from all three.
**Data Shape:** WeakSets hold Request objects (GC-friendly); `requests` dict is id→request for O(1) lookup by control commands; LimitedSets are bounded+expiring collections (maxlen caps memory, expires auto-purges) — revoke memory is FINITE by design.

### Decisive source
```python
# celery/worker/state.py:88-94 — cooperative shutdown checked everywhere
def maybe_shutdown():
    """Shutdown if flags have been set."""
    if should_terminate is not None and should_terminate is not False:
        raise WorkerTerminate(should_terminate)
    elif should_stop is not None and should_stop is not False:
        raise WorkerShutdown(should_stop)
```
```python
# :118-125 — terminal transition
def task_ready(request, successful=False,
               remove_request=requests.pop,
               discard_active_request=active_requests.discard,
               discard_reserved_request=reserved_requests.discard):
    if successful:
        successful_requests.add(request.id)   # feeds dedup-on-redelivery
    remove_request(request.id, None)
    discard_active_request(request)
    discard_reserved_request(request)
```

**Flow:** strategy reserves → pool accept accepts (active) → trace finishes → ready removes. The three-tier membership answers the classic queries: `reserved` = claimed but not yet on a worker, `active` = executing now, `successful` recently-succeeded ids (consumed by build_tracer's dedup short-circuit). Control commands (`scheduled/reserved/active/revoked` in worker/control.py) read these directly. Shutdown is COOPERATIVE: signals set module flags; loops, consumer, and timer callbacks call `maybe_shutdown()` at safe points to raise `WorkerShutdown(1)` / `WorkerTerminate(signum)`.
**Invariant:** (1) A request must be in exactly one of reserved/active at a time; task_ready clears ALL THREE structures plus the dict — missing one leaks prefetch slots forever. (2) `should_terminate is not False` (not just truthiness): 0 as signum must not mean "stop". (3) successful_requests/revoked are bounded — never replace with unbounded sets or long-running workers OOM. (4) These are MODULE globals shared by threads/processes-in-the-main-process only — child processes get copies.
**Probe:** `t/unit/worker/test_state.py::test_task_accepted_and_ready` family (13 tests) pins the add/discard symmetry; `t/unit/worker/test_consumer.py::test_cancel_active_requests_*` exercises ledger-driven shutdown cancellation.
**Retrieve:**
```json
{"project":"ext-celery","query":"task_reserved task_accepted task_ready revoked_tasks","limit":5,"detail":"ids"}
```
## Verdict
Adopt the three-tier ledger with bounded/expiring success and revoke sets, and flag-based cooperative shutdown raised at checkpoint calls. Adapt WeakSet/LimitedSet to your runtime's equivalents (any bounded LRU-with-TTL works). Omit the state-persistence (StateDB) merge format unless workers must share revoke state via shelve.
