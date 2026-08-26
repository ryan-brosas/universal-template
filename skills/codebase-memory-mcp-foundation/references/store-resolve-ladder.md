<!-- capsule-v2 -->
# Store resolve ladder — how do you map a project name to a store handle without creating ghosts or trusting stale verdicts?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the full open→integrity→quarantine→fallback chain behind every tool's project argument?

## Query-open → integrity gate (mutation-guarded) → internal-name fallback scan
**Path/Symbol:** `src/mcp/mcp.c:resolve_store_internal` (2144–2280) + `verify_project_indexed` (2742–2752).
**Signature:** `static cbm_store_t *resolve_store_internal(srv, project, bool mutation_already_held, bool nonblocking_recovery, store_recovery_status_t *status);`
**Data Shape:** Fast path: cached store for same project. Then `<cache>/<project>.db` opened query-only (empty/invalid name ⇒ skip entirely — #1425: SQLite treats "" as anonymous temp DB which then fails integrity and quarantines a relative `.corrupt.<hex>` in the daemon CWD!). Fallback: scan cache dir for the db whose sole internal project row equals the requested name (#704 legacy/twin DBs).

### Decisive source
```c
srv->store = path[0] ? cbm_store_open_path_query(path) : NULL;
if (srv->store) {
    if (!cbm_store_check_integrity(srv->store)) {
        ... acquire project mutation guard ...
        /* The lease may have waited behind a publisher. Re-open and trust
         * only the current generation, never the stale pre-wait verdict. */
        srv->store = cbm_store_open_path_query(path);
        cbm_integrity_verdict_t verdict = ... check_integrity_verdict ...
```

**Flow:** cache hit? → derive path (reject empty) → query-only open → shallow integrity; on failure take project mutation lease, RE-OPEN, run three-way VERDICT on the current generation → TRANSIENT ⇒ close + retry later (never quarantine); CORRUPT ⇒ quarantine to `.corrupt.N` and continue fresh → verify internal project row exists (else close, fall to scan) → fallback scan adopts drifted-name DBs.
**Invariant:** Verdicts must be re-read AFTER waiting on a guard; a NULL store for unknown projects is correct behavior (REQUIRE_STORE surfaces "not indexed").
**Probe:** `tests/test_mcp.c:tool_corrupt_store_cleanup_rechecks_generation_after_guard_wait`, plus `tests/repro/repro_issue557.c` exercising query opens.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "resolve_store_internal", limit: 5 });
```

## Verdict
Adopt the full ladder (cache → guarded verdict → fallback scan) for any named-artifact resolver; adapt quarantine naming; keep the empty-name short-circuit — it prevents a real CWD-pollution bug class.
