<!-- capsule-v2 -->
# Event-loop-bound weighted admission gate with integral demand accounting — why can't this just be asyncio.Semaphore, and how do you measure demand you only see between samples?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What does it take to build an admission gate that a cross-thread controller can retune live, that never revokes granted permits, and whose demand signal survives millisecond-scale holds?

## Loop-bound gate + thread-safe registry + folded permit-seconds
**Path/Symbol:** `backend/python/app/services/resource_governor/gate.py:AdmissionGate` (L60–245: `_bind` 97–111, `_try_admit` 133–151, `acquire` 155–185, `release` 187–194, `slot` 196–209, `drain_demand` 211–229), `StartRateLimiter` (L28–57), `_SAFETY_NET_INTERVAL_SECONDS=1.0` (L25); registry `registry.py:LimitRegistry.set/subscribe` (returns-changed bool; callbacks OUTSIDE the lock, exceptions swallowed); models `PoolDemand.utilisation/has_demand` (L192–200).
**Signature:** `acquire(cost=1, timeout=None) -> bool` (False on timeout, NEVER raises); `slot(cost, timeout)` async-CM yielding the outcome; `release(cost)` clamped `min(cost, in_use)`; `drain_demand() -> PoolDemand` read-and-reset; `StartRateLimiter.try_consume() -> bool`.
**Data Shape:** accumulators folded on state change: `_permit_seconds += in_use × elapsed` since `_last_change`; demand tuple `{permit_seconds, blocked_acquires, total_wait_seconds, completions, max_in_use, rate_limited_acquires}`; utilisation = `permit_seconds / (limit × interval)` capped 1.0.

### Decisive source
```python
# gate.py module docstring + _bind: NOT a Semaphore because (a) limits change
# under the controller's feet from another thread — Semaphore bakes its value
# in; (b) waiters must re-check admission IN PLACE against weighted cost,
# woken by registry subscription, not FIFO rejoin; (c) a second event loop
# using the same gate would silently corrupt counters, so _bind RAISES:
elif loop is not self._loop: raise RuntimeError(...one gate per loop...)

def _try_admit(self, cost):
    limit = self._registry.get(self._pool)          # read EVERY attempt
    # Deadlock guard: oversized request (cost > limit, or limit shrunk to 0)
    # is admitted ALONE when idle rather than waiting forever:
    has_room = self._in_use == 0 or (self._in_use + cost <= limit)
    ...
    if rate_limiter and not try_consume(): self._rate_limited_acquires += 1
    return False   # distinct diagnostic: capacity free but burst-smoothed

# acquire(): poll loop with 1s safety net so a MISSED wakeup can only stall
# a waiter 1s, not forever; event.clear() BEFORE waiting (release sets it).
# release(): folds permit_seconds FIRST, then decrements, then event.set().
```

**Flow:** consumer enters `async with gate.slot(cost=parse_cost(tier,size))` → first use binds gate to the running loop and subscribes to the pool's registry channel → admit path checks room then start-rate token bucket → blocked path polls ≤1s intervals until release()/limit-change wakes it → controller drains accumulators once per sample interval into `PoolDemand` → policy grows a pool only when `has_demand(limit, interval, threshold)` proves real contention (`blocked_acquires > 0` OR utilisation ≥ 0.7 light / 0.3 light-tier).
**Invariant:** (1) Never revoke: shrinking changes only FUTURE acquires (`test_shrink_does_not_revoke_in_flight_permits` :68). (2) Over-release cannot mint permits (`min(cost, in_use)` clamp, :100). (3) Timeout ⇒ False ⇒ backpressure, never an exception (:46). (4) Permit-seconds folding makes thousands of ms-scale Jira block parses VISIBLE to a periodic sampler — point sampling would see nothing (`test_permit_seconds_matches_analytic_integral` :182, `test_massively_concurrent_short_holds_are_visible_to_demand` :202). (5) `rate_limited_acquires` separates "throttled by burst smoother" from "at the concurrency limit" — the warn-log in admission.py names it directly. (6) One gate instance per event loop, enforced loudly.
**Probe:** `tests/unit/services/resource_governor/test_gate.py` :30–215 (weighted acquire/release, timeout-False, oversized-cost-idle-only :56, wake-on-limit-rise :111, wake-on-release :128, second-loop RuntimeError :146, drain-resets :162); `test_demand_accounting.py` (78L dedicated suite); integration `tests/integration/test_small_record_scaling.py` (138L) drives small-record throughput scaling end-to-end.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "AdmissionGate drain_demand StartRateLimiter" --detail ids
```

## Verdict
Adopt the gate+registry+integral-demand trio wholesale for any dynamically-retuned concurrency limit; adopt `StartRateLimiter` when memory allocation happens at START (its whole purpose is spacing allocations, not limiting concurrency). Adapt pool enum and cost weights. Do NOT substitute a plain Semaphore — the tests pin revocation/wakeup/cross-loop behaviours it cannot satisfy. Coverage: dedicated unit suites per file + integration; runner-block caveat in work record [DONE:188].
