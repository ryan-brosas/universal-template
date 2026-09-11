<!-- capsule-v2 -->

# Tag-concurrency slot lease — How does a task hold a concurrency slot reliably across a long run?

**Path/Symbol:** `src/prefect/task_engine.py:SyncTaskRunEngine.start (919-961)` (async twin `1548-1592`); renewal machinery `src/prefect/concurrency/_leases.py` (`_RENEWAL_FRACTION = 0.75`, `_RENEWAL_MAX_ATTEMPTS = 3`, `maintain_concurrency_lease (:177-208)`).

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** What wraps the whole task body so occupancy survives crashes and renewals survive API hiccups?

**Signature:** `_concurrency(names=[f"tag:{tag}" for tag in self.task_run.tags], occupy=1, holder=ConcurrencyLeaseHolder(type="task_run", id=self.task_run.id), lease_duration=60, suppress_warnings=True)`.

**Data Shape:** Slot names are namespaced per-tag (`tag:<tag>`); the holder binds the lease to the task-run id; duration 60s renewed at ~75% elapsed (`_RENEWAL_FRACTION`) by a watcher thread with retry ladder base 1s / cap 10s exponential backoff.

### Decisive source
```python
with _concurrency(
    names=[f"tag:{tag}" for tag in self.task_run.tags],
    occupy=1,
    holder=ConcurrencyLeaseHolder(type="task_run", id=self.task_run.id),
    lease_duration=60,
    suppress_warnings=True,
):
    raise_if_flow_run_suspension_requested()
    self.begin_run()
    try:
        yield
    finally:
        self.call_hooks()

def maintain_concurrency_lease(lease_id, lease_duration, ...):
    with WatcherThreadCancelScope() as cancel_scope:
        stop_event, thread = _start_lease_renewal_thread(...)
        yield
    finally:
        stop_event.set(); thread.join(timeout=2)
```

**Flow:** start() resolves params/names/deps first (NotReady path yields WITHOUT occupying a slot) → enter tag-concurrency with a leased slot → suspension re-check → begin_run → yield body → finally call_hooks → exit releases. Deployment-level leases use the sibling `maintain_concurrency_lease(lease_id, 300, raise_on_lease_renewal_failure=True)` inside setup_run_context (:1117-1122): renewal failures after 3 backoff attempts RAISE when raise_on_failure is set — losing the slot must not silently overrun the limit.

**Invariant:** (1) Occupancy encloses begin_run AND body: acquiring only around user code would let state transitions race slot availability. (2) Leases (not plain counts) are what make crashes self-healing — expiry frees the slot without cleanup; renewal at 75% keeps a 60s lease alive indefinitely while masking sub-10s API outages via the backoff ladder. (3) NotReady parameter-resolution failure exits BEFORE acquisition — deferred tasks must not consume slots they aren't using.

**Probe:** `grep -cF 'names=[f"tag:{tag}" for tag in self.task_run.tags]' src/prefect/task_engine.py` → 2; `grep -c 'lease_duration=60' src/prefect/task_engine.py` → 2; `grep -cF '_RENEWAL_FRACTION = 0.75' src/prefect/concurrency/_leases.py` → 1. Direct tests: `tests/concurrency/test_concurrency_slot_acquisition_with_lease_service.py::TestShouldUseCache` (:450-479 holder-type/tag-name gating) and `tests/test_task_engine.py` engine-start suites.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "concurrency occupy tags suppress_warnings holder", "limit": 4}'
```

## Verdict
Adopt lease-backed slot occupancy with fractional-interval renewal for any bounded-resource gate; adapt limits backend; omit v2-limit server semantics.
