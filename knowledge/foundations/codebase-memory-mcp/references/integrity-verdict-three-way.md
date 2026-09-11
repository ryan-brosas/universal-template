<!-- capsule-v2 -->
# Integrity verdict three-way — why is "can't open" NOT the same as "corrupt"?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the verdict enum distinguish, and what test pins each class?

## HEALTHY / CORRUPT / UNOPENABLE(TRANSIENT) verdict taxonomy
**Path/Symbol:** `src/store/store.c:cbm_store_check_integrity_verdict` + tests/test_store_nodes.c:1305–1360 (`store_integrity_verdict_healthy_is_ok`, `store_integrity_verdict_real_corruption_is_corrupt`, `store_integrity_verdict_unopenable_is_transient_not_corrupt`).
**Signature:** `cbm_integrity_verdict_t cbm_store_check_integrity_verdict(cbm_store_t *s);`
**Data Shape:** HEALTHY: integrity_check returns ok AND single-primary invariant holds. CORRUPT: check reports errors (or >1 primary rows — seeded bogus row case). UNOPENABLE/TRANSIENT: file missing/busy/locked ⇒ never classified corrupt (a concurrent publisher or AV scan is not damage).

### Decisive source
```c
TEST(store_integrity_verdict_healthy_is_ok) { ... }
TEST(store_integrity_verdict_real_corruption_is_corrupt) { ... }
TEST(store_integrity_verdict_unopenable_is_transient_not_corrupt) { ... }
```

**Flow:** open → run PRAGMA integrity_check → apply structural invariants → classify. resolve_store's recovery ladder consumes the verdict (TRANSIENT retries later; CORRUPT quarantines).
**Invariant:** Misclassifying transient unavailability as corruption destroys good databases via quarantine — the third state exists precisely to prevent that.
**Probe:** the three named tests plus `store_integrity_windows_lowercase_drive_issue367` (path normalization edge).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "check_integrity_verdict", limit: 5 });
```

## Verdict
Adopt three-state integrity classification for any cached artifact with quarantine semantics; adapt checks; keep TRANSIENT non-destructive by construction.
