<!-- capsule-v2 -->
# TCP-slow-start concurrency ramp with resource-delta probing — why must warm-start ignore MAX_CONCURRENT_* (and how does exponential growth find the capacity knee safely)?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do you size concurrency limits in a shared cgroup WITHOUT letting the first burst OOM you, and how should the ramp accelerate once headroom is proven?

## Floor start + slow-start doubling + delta-gated steps; shrink re-arms slow start
**Path/Symbol:** `backend/python/app/services/resource_governor/policy.py`: constants L51–151 (`HEAVY_PARSE_WORKING_SET_GB`, slots-per-CPU, EMBEDDING_CPU_RESERVATION, INDEX_SLOTS_PER_PARSE_SLOT=100, MEM_SOFT/HARD/GROW_BAND with post-read cross-clamping), `resolve_ceilings` L216–285, `floor_for/warm_start_limits` L309–349, `_target_for` L360–380, `_growth_step` L383–434, `_record_grow` L437–444, `_reset_for_shrink` L447–462, `heavy_memory_cap` L192–208, `start_rate_limiter_params` L288–306.
**Signature:** `resolve_ceilings(snap, env_parse, env_index, worker_count, *, reserve_embedding_cpus=False) -> Ceilings`; `next_limits(current, snap, ceilings, state, demand, now, interval) -> (Limits, ControllerState)` — PURE (clock/snapshot injected).
**Data Shape:** `PoolState{healthy_streak, cooldown_until, in_slow_start, slow_start_step, prev_grow_mem_pressure, prev_grow_cpu_utilisation}` carried per pool between samples; ceilings resolved ONCE at startup.

### Decisive source
```python
# warm_start_limits docstring — THE incident that shaped this module:
# "An explicit MAX_CONCURRENT_* used to start *at* the ceiling... But a
# limit only bounds new admissions — the governor cannot revoke a permit
# it already granted — so starting wide open lets the first burst commit
# more memory than the cgroup can hold before the first sample even runs,
# and the OOM killer wins that race (MAX_CONCURRENT_PARSING=1000 admitted
# a thousand Docling parses and took the container down). An explicit
# value still raises the ceiling the ramp climbs toward; it no longer
# skips the ramp."

def _growth_step(pool, ceiling, state, snap):        # slow start
    if not state.in_slow_start: return COUNT_POOL_STEP, state   # linear after knee
    if not _is_light_pool(pool):                     # light cost = noise vs Docling;
        ...                                          # delta probe SKIPPED for light
    impact = max(|mem_now - prev_mem|, cpu_delta_or_0)
    if impact >= RESOURCE_DELTA_MODERATE(0.20): return 0, state      # HOLD, keep slow start
    if impact >= RESOURCE_DELTA_LOW(0.05):      return 1, exit_slow_start(state)
    return used_step, replace(state, slow_start_step=used_step*2)    # double

# _reset_for_shrink: ANY shrink clears slow-start memory (in_slow_start=True,
# step=1, baselines=None) so recovery after a pressure incident is EXPONENTIAL
# too, not a linear +1/interval crawl.
```

**Flow:** startup resolves ceilings from CPU quota only (`min(cpu×slots_per_tier, env_cap)`; embedding-CPU reservation subtracted BEFORE slot math so heavy can never reach those cores at any ramp point; memory deliberately NOT consulted at startup — free RAM now predicts nothing five minutes into a batch) → pools warm-start at floors (count pools min(2, ceiling); LIGHT at half-ceiling since per-slot cost ≈ 0 but floor==ceiling would leave the brake nothing to shrink; INDEX at its ceiling — never adapted, adapting it throttled the mostly-waiting pipeline stage and cost ~45s of near-serial startup per deploy) → each sample grows by ≤ one step toward target when healthy+demand confirmed → heavy's target additionally clamped by `heavy_memory_cap = free_gb / HEAVY_PARSE_WORKING_SET_GB` floored at 1 (can hold heavy BELOW warm-start floor when the cgroup truly can't fit another working set).
**Invariant:** (1) Warm-start NEVER honours an operator cap as a starting value — cap raises the ceiling only; the ramp always runs (the pinned incident). (2) Growth requires demand proof (`blocked_acquires>0` or utilisation ≥ threshold) — no speculative growth into idle resources. (3) Delta thresholds compare against the PREVIOUS GROW STEP's snapshot (`_record_grow`), not the previous sample; missing CPU side drops out of the max rather than vetoing. (4) Moderate impact holds WITHOUT abandoning slow start (a noisy sample shouldn't discard confirmed headroom); low impact exits to linear permanently until next shrink. (5) Env overrides are cross-clamped AFTER their own reads (`MEM_HARD = max(read, MEM_SOFT+0.01)` etc.) so overriding one of three can't break MEM_HARD > MEM_SOFT > MEM_SOFT−GROW_BAND. (6) Sustained start-rate = `max(base_rate, ceiling/20)/interval` scales the burst smoother with the ceiling instead of capping admits at 0.5/s forever.
**Probe:** `test_policy.py` :77–943 — `TestResolveCeilings` :77, `TestEmbeddingCpuReservation` :165, `TestHeavyMemoryCap` :221, `TestWarmStartLimits` :264, `TestNextLimitsPressure` :339, `TestHeavyMemoryGate` :468, `TestExponentialGrowth` :754, `TestConfigurableThresholds` :920; rate params `test_rate_limiter.py` (60L).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "_growth_step resolve_ceilings warm_start_limits" --detail ids
```

## Verdict
Adopt floor-warm-start + exponential-slow-start-with-resource-delta-probing as the default posture for ANY resource-adaptive concurrency controller in shared containers; adopt "operator caps raise ceilings, never skip ramps". Adapt constants via env (already env-tunable). Omit the index-pool special case unless your pipeline width is likewise gated elsewhere. Coverage: 1,001L dedicated policy suite pins every branch; runner-block caveat in work record [DONE:188].
