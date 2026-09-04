<!-- capsule-v2 -->
# Store transactions — what's the minimal begin/commit/rollback contract for multi-row edits?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do callers group writes so a mid-sequence failure leaves nothing behind?

## Explicit BEGIN IMMEDIATE / COMMIT / ROLLBACK wrappers
**Path/Symbol:** `src/store/store.c:cbm_store_begin/_commit/_rollback` + tests/test_store_search.c:528 (`store_transaction_commit`), 545 (`store_transaction_rollback`), 564 (`store_bulk_write_mode`).
**Signature:** `int cbm_store_begin(cbm_store_t *s);` / `_commit(s)` / `_rollback(s);`
**Data Shape:** Begin issues `BEGIN IMMEDIATE` (write lock up front — avoids SQLITE_BUSY surprises mid-transaction); commit returns final rc; rollback is safe to call after any failure. Bulk mode composes on top (see bulk-write capsule).

### Decisive source
```c
TEST(store_transaction_commit) { ... }
TEST(store_transaction_rollback) { ... }
```

**Flow:** caller: begin → multiple upserts → commit; any step failing ⇒ rollback and surface first error. Coverage-replace, artifact publish internals all use this trio.
**Invariant:** Never interleave two transaction users on one store handle without nesting discipline (this codebase uses flat, non-nested transactions).
**Probe:** the three named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_begin", limit: 5 });
```

## Verdict
Adopt BEGIN IMMEDIATE semantics for write bursts; adapt to your driver; keep rollback-on-any-failure as a lint rule.
