<!-- capsule-v2 -->
# Governor pressure split: baseline-credited growth vs raw-occupancy brakes — how do you share a cgroup with an idle co-tenant service without either pinning at the floor or OOMing?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai` (fresh gen 2026-08-23T13:56Z; short-name `pipeshub-ai` is STALE pre-drift). **Question:** When a container hosts your workload plus a multi-GiB idle service (Docling model weights), how must memory pressure be computed so growth is still possible AND the shrink brake trips before the kernel OOM killer acts?

## Two readings of one working set, chosen by decision direction
**Path/Symbol:** `backend/python/app/services/resource_governor/models.py:ResourceSnapshot.mem_usable_bytes/mem_pressure/mem_pressure_raw` (L32–124); consumers `policy.py:_next_pool_limit` (brake selects RAW at L503, grow uses credited `pressure` at L494/L538–543), `probe.py:BaselineMemoryTracker.adjust` (L383–400).
**Signature:** `mem_pressure -> float | None`; `mem_pressure_raw -> float | None`; both divide by `mem_limit_bytes`; tracker `adjust(working_set, limit_bytes) -> (adjusted_working_set | None, baseline_used | None)`.
**Data Shape:** frozen dataclass carries BOTH `mem_working_set_bytes` (baseline-subtracted) and `mem_working_set_raw_bytes`, plus `mem_baseline_bytes`; any unproducible field is `None` and callers treat unknown as "assume nothing", never as zero.

### Decisive source
```python
# models.py — why BOTH sides of the credited ratio exclude the baseline:
# "Dividing the baseline-adjusted working set by the *raw* limit would cap
# the achievable reading at 1 - baseline/limit; with the multi-GB baseline
# of an all-in-one container that ceiling falls below MEM_SOFT, and no
# amount of real pressure could ever trip the brake before the kernel
# OOM-kills the container."
usable   = limit - (baseline or 0)
pressure = working_set / usable            # credited → governs GROWTH only
# ...but a full cgroup must still read ~1.0: if baseline >= usable, fall
# back to the RAW ratio rather than reporting a healthy-looking ~0.0.
# mem_pressure_raw docstring: "Always >= mem_pressure... Growth needs that
# credit (otherwise a co-located service's idle footprint pins every pool
# at its floor forever), but a shrink decision must not inherit it — the
# container has to be able to brake while there is still headroom left to
# brake into."  policy._next_pool_limit:
if brake_pressure >= MEM_HARD: return max(floor, current // 2), incident_reset
if brake_pressure >= MEM_SOFT or cpu_brake: return max(floor, current - 1), shrink_reset
```

**Flow:** probe reads cgroup limit + working set each sample → `BaselineMemoryTracker` subtracts the co-tenant baseline (env override wins outright; else auto-calibrated as the low-water mark after a 3-sample warm-up, ratcheting down never up, capped at 50% of the limit) → controller's control law (`policy._next_pool_limit`) SHRINKS on `mem_pressure_raw` (true kernel occupancy) but GROWS on `mem_pressure` (credited reading) whenever `pressure < MEM_SOFT − GROW_BAND`, demand exists (`blocked_acquires > 0` or utilisation ≥ threshold), and no cooldown is active → `_free_memory_gb`/`heavy_memory_cap` likewise use RAW bytes because physical freeness doesn't care which process holds the pages.
**Invariant:** (1) Direction asymmetry is the whole design — crediting on shrink pushes effective MEM_SOFT/MEM_HARD up by the baseline's share (3GiB of 12GiB turns 70%/80% into 78%/85% real) and leaves too little headroom for the brake to matter; test pins exactly this regression (`TestBrakeUsesRawPressure`: credited reading looks healthy while raw ≥ MEM_SOFT+0.06 still shrinks 8→7; raw ≥ MEM_HARD+0.02 halves 8→4; growth still credits the baseline and ramps floor→floor+1). (2) If baseline swallows the whole limit, report the RAW ratio (~1.0), not ~0.0 — never read as idle. (3) Baseline auto-calibration applies NO subtraction during the warm-up window (early samples behave like pre-fix raw behaviour) and never increases afterward. (4) `None` fields veto only the specific decision they'd poison (unknown pressure freezes growth via streak reset; CPU delta missing drops out of the impact `max()` instead of vetoing growth).
**Probe:** `tests/unit/services/resource_governor/test_policy.py::TestBrakeUsesRawPressure` :398–467 (soft/hard/growth-credit trio); `test_probe.py` :261–350 (explicit override incl. zero-is-valid, malformed→auto, warmup :296, low-water apply :306, ratchet :316, never-increase :331, floor-at-zero :341, unknown-working-set :350).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "mem_pressure_raw BaselineMemoryTracker" --detail ids
```

## Verdict
Adopt the two-reading pattern verbatim for ANY admission controller sharing a cgroup with a resident co-tenant: credit the baseline on both sides of the growth ratio, brake on raw occupancy, keep both fields on the snapshot for observability logging. Adapt thresholds (MEM_SOFT/HARD/GROW_BAND are env-tunable here) and the calibration sample count. Omit nothing. Coverage: direct tests exist for every branch cited; runner-block caveat recorded in work record [DONE:188].
