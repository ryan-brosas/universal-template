<!-- capsule-v2 -->
# Autoscale ladder — when does the pool grow and shrink, and why is scaling down harder?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What demand signal drives pool resizing, what prevents flapping, and how do shrink failures surface?

## Autoscaler + WorkerComponent
**Path/Symbol:** `celery/worker/autoscale.py:WorkerComponent` (:26-48, conditional bootstep requires=(Pool,)), `Autoscaler(bgThread)` (:51-154); env knob `AUTOSCALE_KEEPALIVE` default 30s.
**Signature:** `Autoscaler(pool, max_concurrency, min_concurrency=0, worker=None, keepalive=AUTOSCALE_KEEPALIVE, mutex=None)`; `body()` = `with mutex: maybe_scale(); sleep(1.0)`.
**Data Shape:** Demand metric `qty = len(state.reserved_requests)` (the reserved ledger); supply `processes = pool.num_processes`; `_last_scale_up` monotonic timestamp gates scale-down.

### Decisive source
```python
# celery/worker/autoscale.py:79-91 — the direction decision
def _maybe_scale(self, req=None):
    procs = self.processes
    cur = min(self.qty, self.max_concurrency)
    if cur > procs:
        self.scale_up(cur - procs)
        return True
    cur = max(self.qty, self.min_concurrency)
    if cur < procs:
        self.scale_down(procs - cur)
        return True

def scale_down(self, n):
    if self._last_scale_up and (
            monotonic() - self._last_scale_up > self.keepalive):
        return self._shrink(n)          # anti-flap: cool-down after growth
```
```python
# :124-131 — shrink can legitimately fail
def _shrink(self, n):
    try:
        self.pool.shrink(n)
    except ValueError:
        debug("Autoscaler won't scale down: all processes busy.")
```

**Flow:** background thread ticks 1/s under a lock (DummyLock when on the event loop; also hooked into `on_task_message` + hub keepalive for green mode) → target = clamp(qty, [min, max]) → grow by deficit (immediate, updates `_last_scale_up`) or shrink by surplus only after keepalive quiet period → `maybe_scale` calls `pool.maintain_pool()` after any change → remote `update(max,min)` shrinks BEFORE raising max_concurrency and adjusts consumer prefetch via `_update_consumer_prefetch_count`.
**Invariant:** (1) Scale-UP is instant, scale-DOWN is delayed by keepalive — asymmetric on purpose to absorb bursts. (2) ValueError from pool.shrink means "no idle process to remove" — it's a debug log, never an error; a porter who lets it raise kills the autoscaler thread. (3) qty counts RESERVED requests (queued+running), not active — backlog drives growth. (4) update() ordering (shrink then set new max) avoids overshoot.
**Probe:** `t/unit/worker/test_autoscale.py::class test_Autoscaler` (14 tests) pins grow/shrink/update math incl. keepalive gating.
**Retrieve:**
```json
{"project":"ext-celery","query":"Autoscaler maybe_scale scale_down keepalive shrink","limit":5,"detail":"ids"}
```
## Verdict
Adopt: reserved-count demand signal, clamped targets, one-second tick, keepalive anti-flap, ValueError-as-busy semantics. Adapt bgThread and process-pool shrink primitives. Omit prefetch rebalancing hooks if your broker has no per-consumer credit system.
