<!-- capsule-v2 -->
# AsynPool timer-ref deadline chain — how do soft and hard time limits cooperate on an event loop?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How are per-job soft→hard deadlines armed, chained, cancelled, and cleaned up without leaking timer handles?

## _create_timelimit_handlers
**Path/Symbol:** `celery/concurrency/asynpool.py:AsynPool._create_timelimit_handlers` (:549-605); consumers `_on_soft_timeout` (:578), `_on_hard_timeout` (:595); request-side consumption in `celery/worker/request.py:on_timeout` (:416).
**Signature:** `on_timeout_set(R, soft, hard)` / `on_timeout_cancel(R)` installed onto the pool; hub primitive `hub.call_later(delay, fun, *args)` returning a cancellable tref.
**Data Shape:** `self._tref_for_id = WeakValueDictionary()` keyed by job id; values are hub timer refs. `R._job` is the pool job handle carried by the result object.

### Decisive source
```python
# celery/concurrency/asynpool.py:554-604
def on_timeout_set(R, soft, hard):
    if soft:
        trefs[R._job] = call_later(
            soft, self._on_soft_timeout, R._job, soft, hard, hub)
    elif hard:
        trefs[R._job] = call_later(hard, self._on_hard_timeout, R._job)
...
def _on_soft_timeout(self, job, soft, hard, hub):
    if hard:
        # re-arm for the REMAINING window
        self._tref_for_id[job] = hub.call_later(
            hard - soft, self._on_hard_timeout, job)
    try:
        result = self._cache[job]
    except KeyError:
        pass  # job ready — finished before the deadline fired
    else:
        self.on_soft_timeout(result)
    finally:
        if not hard:
            self._discard_tref(job)
```

**Flow:** job accepted → `on_timeout_set` arms soft (or hard-only) → soft fires: warn + notify request (`Request.on_timeout(soft=True)`) and IF a hard limit exists re-arm a new tref for exactly `hard - soft` → hard fires: kill the child (`terminate_job`), mark failure via the request path → normal completion calls `on_timeout_cancel` → `_discard_tref` pops + cancels.
**Invariant:** (1) The `_cache[job]` KeyError branch is the race guard: if the job completed between timer fire and handler run, the timeout is silently dropped ("job ready") — never treat missing cache as an error. (2) `_discard_tref` swallows `(KeyError, AttributeError)` BY DESIGN (comment: "out of scope") — double-cancel is normal. (3) WeakValueDictionary means a garbage-collected result object drops its tref mapping automatically; the explicit pop is just prompt cleanup. (4) Hard delay must be computed as remaining (`hard - soft`), not absolute — re-arming with `hard` would double the budget.
**Probe:** `t/unit/worker/test_request.py::test_on_soft_timeout` (:1278) pins the warn-not-kill boundary; `t/unit/concurrency/test_concurrency.py::test_interface_on_soft_timeout` (:144) pins pool-level hook defaults.
**Retrieve:**
```json
{"project":"ext-celery","query":"_create_timelimit_handlers _on_soft_timeout _tref_for_id","limit":5,"detail":"ids"}
```
## Verdict
Adopt the arm/chain/cancel triad with the remaining-window arithmetic and both silent-race guards. Adapt kombu's hub.call_later to your event loop's timers; keep the WeakValueDictionary trick if results are objects. Omit the synack/greenlet-specific write scheduling of asynpool if your pool is thread-based.
