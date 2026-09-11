<!-- capsule-v2 -->
# Memory budget resolver — how do you turn total RAM + env overrides into a safe worker budget?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Where should env-var parsing live so callers never re-derive budget math, and how do tiers and hard caps compose?

## Pure resolver with strict-parse override
**Path/Symbol:** `src/foundation/mem.c:cbm_mem_resolve_budget` (198–246) + `cbm_mem_ram_fraction_for_total` (188–196).
**Signature:** `cbm_mem_budget_t cbm_mem_resolve_budget(size_t total_ram, double ram_fraction, const char *budget_mb);` (+ `_capped` variant)
**Data Shape:** Result = {budget bytes, source token ("ram_fraction"|"CBM_MEM_BUDGET_MB"), clamped, invalid, hard_capped}. Tiers: ≤16 GiB → 0.25, ≤32 GiB → 0.35, else 0.50. Worker-only cap: user override still wins if LOWER; otherwise min(default, hard_cap).

### Decisive source
```c
/* Strict parse ... reject trailing garbage (`*end`), overflow (errno==ERANGE),
 * and non-positive values. This turns a fat-fingered value (e.g. "8GB", or a
 * 20-digit typo) into a clean fallback-with-warning rather than a silently
 * wrong budget. */
```
```c
/* Worker-only initialization cap carried on the build-bound internal argv.
 * The existing user override is still resolved first; a lower explicit
 * CBM_MEM_BUDGET_MB wins, while a larger/default budget is capped. */
```

**Flow:** read total RAM once → tier the default fraction → if override string present, STRICTLY parse (strtoll + endptr + ERANGE + >0); invalid ⇒ fall back to fraction-derived with warning flag → clamp to total when exceeded (clamped=true) → supervised workers additionally apply min(resolved, hard_cap) with its own flag → `cbm_mem_init` consumes exactly this struct so parse logic lives in ONE place.
**Invariant:** The resolver reads no globals/env — pure function of arguments — which is what makes it unit-testable and lets init/cap variants share one code path.
**Probe:** `tests/test_mem.c:mem_ram_fraction_16gb_tier/32gb_tier/large_host`, `mem_worker_budget_zero_workers`, and the strict-parse matrix around test_mem.c:461–480.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_mem_resolve_budget", limit: 5 });
```

## Verdict
Adopt the pure-resolver pattern with explicit clamped/invalid/hard_capped flags for any resource budgeting; adapt tier thresholds to your deployment sizes; omit the RSS-based pressure polling if you only need startup budgets.
