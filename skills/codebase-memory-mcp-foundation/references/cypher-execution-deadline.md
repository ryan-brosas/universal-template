<!-- capsule-v2 -->
# Cypher execution deadline — how do you bound a user-supplied graph query language without killing legitimate heavy queries?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Where do wall-clock checks go in an executor so a runaway query aborts but normal ones never notice?

## Thread-local deadline sampled every 1024 iterations
**Path/Symbol:** `src/cypher/cypher.c:cypher_deadline_arm` / `cypher_deadline_exceeded` (2840–2862) + `cbm_cypher_execute` (4892–4977).
**Signature:** `int cbm_cypher_execute(cbm_store_t *store, const char *query, const char *project, int max_rows, cbm_cypher_result_t *out);` — budget: `CYPHER_DEADLINE_BUDGET_MS 30000`, check mask `0x3FF`.
**Data Shape:** Thread-local absolute deadline (armed at query start); test hook `cbm_cypher_test_set_deadline_ms(0)` trips on the FIRST hot-loop check; negative restores default.

### Decisive source
```c
/* Wall-clock execution deadline (#601). The row ceiling above only fires once
 * [results are materialised] ... the caller just hangs. A monotonic deadline aborts ... */
static _Thread_local uint64_t g_cypher_deadline_ms = 0; /* absolute; 0 = disarmed */
#define CYPHER_DEADLINE_BUDGET_MS 30000  /* 30s: generous for legit heavy queries */
#define CYPHER_DEADLINE_CHECK_MASK 0x3FF /* sample the clock every 1024 iterations */
...
if ((bi & CYPHER_DEADLINE_CHECK_MASK) == 0 && cypher_deadline_exceeded()) { ... }
```

**Flow:** arm deadline from override-or-default → every cross-product/binding loop iteration ANDs its counter with the mask → on wrap, compare CLOCK_MONOTONIC against the deadline → exceeded ⇒ abort with a typed error before materializing more rows.
**Invariant:** Sampling must live in EVERY unbounded loop (three distinct sites), not just one; the check is cheap enough that legit queries pay ~nothing; thread-local keeps concurrent queries independent.
**Probe:** `tests/test_cypher.c:cypher_exec_deadline_aborts_runaway_query_issue601` (budget 0 = RED without the fix: query completes) and `cypher_exec_deadline_allows_normal_query_issue601`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_cypher_execute", limit: 5 });
```

## Verdict
Adopt armed-deadline + masked sampling for any interpreter/DSL you embed; adapt the budget constant to your SLO; omit the test hook in production builds if you can inject time instead.
