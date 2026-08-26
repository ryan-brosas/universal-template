<!-- capsule-v2 -->

# Pending/Paused poisson backoff poll — How does an engine wait out orchestration deferral without hammering the API?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** What is the sleep schedule while a run's proposed state keeps coming back Pending/Paused?

## Clamped Poisson intervals, capped backoff count

**Path/Symbol:** `src/prefect/task_engine.py:SyncTaskRunEngine.begin_run (516-554)` (async twin `1127-1179`); sampler `src/prefect/utilities/math.py:clamped_poisson_interval (43-61)` with helpers `poisson_interval`, `lower_clamp_multiple`, `exponential_cdf`.

**Signature:** loop constant `BACKOFF_MAX = 10` (:130); `clamped_poisson_interval(average_interval=backoff_count, clamping_factor=0.3) -> float`.

**Data Shape:** `backoff_count` grows 1..10 then freezes at 10 forever (cap applies to the AVERAGE, not the attempt count — polling continues indefinitely).

### Decisive source
```python
backoff_count = 0
while state.is_pending() or state.is_paused():
    if backoff_count < BACKOFF_MAX:
        backoff_count += 1
    interval = clamped_poisson_interval(
        average_interval=backoff_count, clamping_factor=0.3
    )
    time.sleep(interval)
    state = self.set_state(new_state)
```

**Flow:** propose Running → if still Pending/Paused (orchestration deferred: concurrency slot waiting, pause hold, upstream NotReady) → sample jittered interval whose average ramps 1s..10s → sleep (async twin uses `anyio.sleep`) → re-propose SAME Running state → exit loop as soon as state leaves Pending/Paused → then `call_hooks(state)` fires on_running hooks once actually Running.

**Invariant:** (1) The random draw is POISSON-clamped, not uniform: upper bound = avg×1.3, lower bound chosen so the mean stays ≈avg (`lower_clamp_multiple` balances probability mass around the median); naive `random.uniform(0, avg)` would halve the effective delay. (2) The cap freezes the AVERAGE at 10s but never aborts — a long queue wait is expected, not fatal. (3) Re-proposal uses the same `new_state` object each iteration; constructing fresh states would multiply state history rows. (4) `clamping_factor <= 0` raises ValueError (guard in sampler).

**Probe:** `grep -c 'BACKOFF_MAX = 10' src/prefect/task_engine.py` → 1; `grep -c 'clamped_poisson_interval' src/prefect/task_engine.py` → 3. Direct tests: `tests/utilities/test_math.py:22 test_clamped_poisson_intervals` and `:71 test_clamped_poisson_interval_rejects_nonpositive_clamping_factor`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "begin_run pending paused backoff", "limit": 4}'
```

## Verdict
Adopt the mean-preserving clamped-Poisson poll for any wait-out-deferral loop against a remote arbiter; adapt caps to your SLA; omit the Prefect state names driving it.
