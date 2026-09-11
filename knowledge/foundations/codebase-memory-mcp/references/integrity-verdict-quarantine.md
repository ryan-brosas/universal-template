<!-- capsule-v2 -->
# Integrity verdict — is this DB corrupt, or did I just lose a lock race?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you quarantine a damaged database WITHOUT destroying healthy ones during concurrent access?

## Three-way verdict before quarantine
**Path/Symbol:** `src/store/store.c:cbm_store_check_integrity_verdict` (970–1051) with `st_rc_is_transient` (958–968).
**Signature:** `cbm_integrity_verdict_t cbm_store_check_integrity_verdict(cbm_store_t *s);`
**Data Shape:** Returns `OK` / `CORRUPT` / `TRANSIENT`. Transient codes: `SQLITE_BUSY`, `SQLITE_LOCKED`, `SQLITE_IOERR_LOCK`, `SQLITE_IOERR_BLOCKED`.

### Decisive source
```c
/* SQLITE_BUSY / SQLITE_LOCKED happen when another connection holds the writer
 * lock — they are NOT evidence of corruption, yet the bare cbm_store_check_
 * integrity() treats any prepare failure as "corrupt". This helper backs the
 * verdict API so the quarantine path stops destroying healthy DBs (#1206,#1037). */
static bool st_rc_is_transient(int rc) {
    switch (rc) { case SQLITE_BUSY: case SQLITE_LOCKED:
    case SQLITE_IOERR_LOCK: case SQLITE_IOERR_BLOCKED: return true; default: return false; } }
...
/* Deep check walks btrees (quick_check(1)) — shallow passes for torn node/
 * edge btrees under an intact projects table. Runs only on quarantine paths. */
```

**Flow:** no handle ⇒ TRANSIENT (an open failure says nothing about contents) → shallow projects-table check with transient-vs-corrupt classification on every prepare/step failure → root_path sanity probe → `PRAGMA quick_check(1)` btree walk → only a confirmed CORRUPT verdict triggers rename-to-`.corrupt.N`; TRANSIENT closes the store and retries on next access.
**Invariant:** Never answer "damaged" to the lock-race question — a spurious quarantine under concurrency renames HEALTHY databases. The deep check is O(db-size) and must stay off hot opens.
**Probe:** `tests/test_store_nodes.c:store_integrity_verdict_healthy_is_ok`, `store_integrity_verdict_real_corruption_is_corrupt`, `store_integrity_verdict_unopenable_is_transient_not_corrupt`; caller discipline pinned by `tests/test_mcp.c:tool_corrupt_store_cleanup_rechecks_generation_after_guard_wait`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_check_integrity_verdict", limit: 5 });
```

## Verdict
Adopt the three-way verdict and the re-open-after-wait discipline (trust only the CURRENT generation's verdict); adapt the specific transient code list to your SQLite version; omit quick_check from hot paths — it exists solely to gate destructive decisions.
