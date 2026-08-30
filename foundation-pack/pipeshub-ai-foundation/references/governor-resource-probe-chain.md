<!-- capsule-v2 -->
# Cross-platform no-root resource probe — how do you read cgroup CPU/memory truthfully (delta-based utilisation, baseline calibration, never-raise) without psutil?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What does a dependency-free container resource probe get wrong by default, and what chain of fallbacks keeps every field best-effort?

## Resolution ladders + delta-only utilisation + host-wide counter normalisation
**Path/Symbol:** `backend/python/app/services/resource_governor/probe.py`: `_resolve_cgroup_path` L92–129, memory ladders `_cgroup_v2_memory`/`_cgroup_v1_memory`/`_proc_meminfo_memory`/`_psutil_memory`/`_windows_memory`/`_resolve_memory` L149–299, `BaselineMemoryTracker` L314–400, quota `_cgroup_v2_cpu_quota`/`_cgroup_v1_cpu_quota`/`_affinity_cpu_count`/`_resolve_cpu_quota` L408–453, usage counters + `_HOST_WIDE_CPU_SOURCES` L529–560, PSI `_read_psi_avg10`/`_cpu_pressure` L574–594, `SystemResourceProbe.snapshot/_snapshot_unguarded` L602–696.
**Signature:** `snapshot() -> ResourceSnapshot` — whole method blanket-guarded; failure degrades to an all-None `source="error"` snapshot (controller retries once at construction for the startup cgroup-mount race).
**Data Shape:** cumulative counters diffed across samples: `utilisation = Δusec / (elapsed × 1e6 × denominator)`; throttled ratio from `Δthrottled_usec`; PSI avg10 read as-is ÷100.

### Decisive source
```python
# Module docstring — the two lies a naive probe tells:
# "CPU *utilisation* is derived from the delta between two cumulative-
# counter reads divided by wall-clock elapsed time — NEVER from
# psutil.cpu_percent() or getloadavg(), both of which alias short bursts
# and under-report exactly the small-record (Jira/Confluence) workload
# this system must scale up for."
_HOST_WIDE_CPU_SOURCES = {"proc_stat", "psutil"}
# "/proc/stat's 'cpu ' line and psutil.cpu_times() are both HOST-WIDE
# aggregates. A delta from one of these must be normalised by the host's
# CPU count, never by cpu_quota — a small container on a big host would
# otherwise see a wildly inflated 'utilisation' and trip the CPU brake
# despite being idle itself."  (Left None if host count unknown: no
# false brake beats a fake one.)
if cpu_usage_usec is not None and self._prev_cpu_usec is not None \
   and cpu_source == self._prev_source:      # cross-source deltas are
    ...                                       # MEANINGLESS: treat as first sample

# Working set = current − inactive_file (page cache is not residency);
# v1 sentinel 2^63−4096 means "no limit" → fall through the WHOLE ladder
# to a source that can supply limit+working_set TOGETHER ("all or nothing").
```

**Flow:** per sample → resolve limit+working-set as a PAIR via cgroup-v2 → v1 → /proc/meminfo → psutil → platform sysconf/ctypes → tracker subtracts co-tenant baseline (env override > low-water-mark auto-calibration, capped at 50% of limit) → resolve CPU QUOTA (cpu.max → cfs_quota/period → affinity → cpu_count) → diff USAGE against previous sample only when source matches → read PSI `cpu.pressure` avg10 → emit snapshot with `source="mem=…,cpu=…"` provenance string; controller runs it via `asyncio.to_thread` so file I/O never blocks the loop.
**Invariant:** (1) Delta utilisation only within one counter source — a fallback switch resets to "first sample". (2) Host-wide sources normalise by host CPUs, container-scoped by quota — mixing them either fakes saturation or hides it (`test_container_scoped_quota_does_not_pair_with_host_wide_proc_stat` :156). (3) Every read returns `(None, None)` rather than a partial pair — an unmatched limit/usage combo poisons ratios. (4) Page-cache subtraction (`inactive_file`) is what makes working set ≈ RSS. (5) The probe can NEVER raise into the governor's sample loop (blanket except → error snapshot). (6) `/proc/self/cgroup` relative-path join handles host-mounted non-namespaced cgroupfs.
**Probe:** `test_probe.py` :49–456 — v2/v1 reads :49/:72, max-sentinel fall-through :60/:83, meminfo :93, none-fields-not-exception :106, quotas :121/:125/:132, usage sources :139/:145/:151, host-wide pairing :156, `/proc/self/cgroup` resolution :191/:203, first-sample-None :217, two-sample-delta :225, snapshot-never-raises :243, full baseline battery :261–350.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "BaselineMemoryTracker SystemResourceProbe _resolve_memory" --detail ids
```

## Verdict
Adopt the ladder structure and the three anti-lies (delta-utilisation, host-vs-container denominators, paired-or-nothing reads) for any containerised backpressure system. Adapt platform coverage as needed. Omit the Windows ctypes branch on Linux-only hosts. Coverage: dedicated 456L suite incl. tmp_path cgroup fixtures; runner-block caveat in work record [DONE:188].
