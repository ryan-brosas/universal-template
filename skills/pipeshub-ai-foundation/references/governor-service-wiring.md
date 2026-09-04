<!-- capsule-v2 -->
# Governor process wiring: memoised gates, thread-owned loops, and the OOM incident fast path — how do five services share one admission controller without deadlocking or leaking?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How is the ResourceGovernor actually instantiated, sampled, and consumed across HTTP routes and Kafka/Redis worker threads — including shutdown ordering and the faster-than-sampling emergency path?

## One governor per process; gates bind to whichever loop asks; incidents bypass sampling
**Path/Symbol:** `backend/python/app/services/resource_governor/controller.py:ResourceGovernor.__init__/gate/run/_sample_once/report_memory_incident/close/stats` (L59–417; state-lock span L269–287; incident path L356–375); consumers `parsing_main.py` :244–254 + `docling_main.py` :96–112 (`create_task(governor.run())` in lifespan), `services/messaging/kafka/consumer/indexing_consumer.py` :154–172 (worker-thread loop creates gates), `services/messaging/consumer_concurrency.py` :294–439 (`acquire_parsing_slot` dual primitive), `modules/parsers/pdf/pdf_rasterizer.py` :39–46+221–226 (module-global setter + incident report).
**Signature:** `gate(pool) -> AdmissionGate` (memoised under lock; second DIFFERENT loop reusing it hits the gate's RuntimeError); `run()` cancellable sample loop with jittered sleep + exception-swallowing; `report_memory_incident(reason)` any-thread; `close()` after stop.
**Data Shape:** three locks with strict roles: `_state_lock` guards registry-snapshot→policy→writes TOGETHER; `_gates_lock` only gate creation/enumeration; `_stats_lock` last snapshot/demand.

### Decisive source
```python
async def _sample_once(self):
    snapshot = await asyncio.to_thread(self._probe.snapshot)  # file I/O off-loop
    demand = self._drain_all_demand()
    with self._state_lock:
        # Lock held across read→compute→write so report_memory_incident()
        # (another thread) can't have its emergency halving CLOBBERED by a
        # sample that read the registry before the incident but writes after.
        new_limits, new_state = next_limits(current, snap=snapshot, ...)
        self._state = new_state
        for pool in Pool:
            if self._registry.set(pool, new_value): changed.append(...)

def report_memory_incident(self, reason):     # BrokenProcessPool handler /
    with self._state_lock:                    # MemoryError catch — reacts
        self._registry.set(Pool.HEAVY_PARSE,
                           max(floor, current // 2))   # immediate HALF
        self._state = ...cooldown_until = now + INCIDENT_COOLDOWN_SECONDS...

# kafka indexing_consumer (worker THREAD owns its own event loop):
self.worker_loop = asyncio.new_event_loop()
asyncio.set_event_loop(self.worker_loop)
if self.governor is not None:
    self.indexing_semaphore = self.governor.gate(Pool.INDEX)  # binds HERE
```

**Flow:** each service main builds ONE governor (uvicorn `PARSING_UVICORN_WORKERS` divides ceilings since sibling workers share the cgroup; `reserve_embedding_cpus=await is_local_cpu_embedding_configured(...)`) → lifespan task runs `governor.run()` forever → HTTP routes call `governor.gate(gate_pool(classify(ext,mime)))` on the uvicorn loop; messaging workers call it inside their own thread-spawned loop — the memoisation plus per-gate loop binding makes cross-loop misuse loud instead of corrupt → PDF rasterizer catches worker OOM/BrokenProcessPool and calls `set_resource_governor(governor)`'d handle's `report_memory_incident` — halving lands immediately, no 15s sample wait → shutdown: cancel sample task, then `governor.close()` unsubscriptions (a gate outliving its loop would bounce callbacks onto a closed loop).
**Invariant:** (1) Sample-failure keeps PREVIOUS limits (log-and-continue) — probing is advisory, admission must not flap on a bad read. (2) Incident halving and periodic sampling serialise on `_state_lock` precisely so the faster path can't be undone by stale-read writes. (3) Gates must be created ON the loop that uses them; the governor tolerates any number of consumer loops but each gate belongs to exactly one. (4) `worker_count>1` divides CEILINGS at startup — per-process governors must sum below the cgroup, not each claim it. (5) `stats()` merges three locks' snapshots and is safe from any thread for health endpoints.
**Probe:** `tests/unit/services/resource_governor/test_controller.py` :1–228 (init-retry-on-error-probe, sample-loop advance, incident halving + cooldown, close-unsubscribes); consumer-side `tests/unit/services/messaging/test_consumer_concurrency_governor.py`, `test_indexing_consumer.py`, `tests/unit/test_parsing_routes.py`, `tests/integration/test_adaptive_concurrency_pressure.py` :1–220 (220L pressure integration).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "ResourceGovernor report_memory_incident _sample_once" --detail ids
```

## Verdict
Adopt the wiring shape — single governor per process, memoised loop-bound gates, `to_thread` probing, lock-spanned sample commits, module-global setter for deep layers needing the incident fast path — for any multi-service shared-cgroup deployment. Adapt pool names and the specific incident trigger. Omit the legacy semaphore fallback branches if greenfield. Coverage: dedicated controller suite + consumer suites + 220L integration; runner-block caveat in work record [DONE:188].
