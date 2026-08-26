<!-- capsule-v2 -->
# Scale-fit regression gate — how do you assert "this pass stays linear" in CI without timing flakes?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you turn complexity growth into a deterministic assertion instead of a wall-clock hope?

## Pure log-ratio exponent k = log(T2/T1)/log(n2/n1)
**Path/Symbol:** `src/foundation/profile.c:cbm_scale_fit_k` (125–131) + probe struct usage (133–186) + tests tests/test_diagnostics.c:581–605 and suite tests/test_complexity.c.
**Signature:** `double cbm_scale_fit_k(long first_n, long first_us, long last_n, long last_us);`
**Data Shape:** Returns the fitted exponent k; −1.0 for degenerate input (first_n≤0, first_us≤0, last_us≤0, last_n≤first_n). Warn threshold CBM_SCALE_WARN_K; n·log·n must NOT be mistaken for quadratic.

### Decisive source
```c
/* k = log(T_last / T_first) / log(n_last / n_first) */
return log((double)last_us / (double)first_us) / log((double)last_n / (double)first_n);
...
/* These pin the arithmetic ... deliberately WITHOUT timing anything. A test that
 * tried to prove the detector works by generating a genuinely quadratic workload
 * would be asserting on the scheduler, and would go flaky on a loaded CI box —
 * so the fit is a pure function and gets fed synthetic points instead. */
ASSERT_TRUE(cbm_scale_fit_k(1000, 1000, 8000, 64000) > 1.99);  /* 8x items, 64x time */
ASSERT_TRUE(k_nlogn > 1.0 && k_nlogn < CBM_SCALE_WARN_K);
```

**Flow:** scale probes checkpoint (n, elapsed-µs) at size milestones during real runs → end-of-run fits first→last points → k above warn threshold emits a scaling diagnostic → CI additionally feeds SYNTHETIC point pairs to the pure function so the classifier itself is pinned without any timing dependence.
**Invariant:** Never assert on measured wall-clock in shared CI; separate the pure fit (unit-tested with synthetic points) from production measurement (diagnostics only).
**Probe:** `tests/test_diagnostics.c:scale_fit_k_recognises_linear_and_quadratic_growth`, `scale_fit_k_rejects_degenerate_input`; live corpus linearity via `tests/test_complexity.c:complexity_replicated_modules_scale_linearly`, `complexity_perfile_registry_work_is_linear`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_scale_fit_k", limit: 5 });
```

## Verdict
Adopt pure-function fit + synthetic-point unit pins + real-corpus diagnostics separation; adapt thresholds to your SLOs; omit the soak-script discovery hooks outside daemon deployments.
