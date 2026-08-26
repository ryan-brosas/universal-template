<!-- capsule-v2 -->
# Passive checkpoint — why checkpoint WITHOUT truncating the WAL?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does periodic maintenance do to WAL growth, and why not TRUNCATE?

## PRAGMA wal_checkpoint(PASSIVE) preserving live readers
**Path/Symbol:** `src/store/store.c` checkpoint hook + tests/test_store_checkpoint.c:98 (`checkpoint_does_not_truncate_wal`).
**Signature:** `cbm_store_exec(s, "PRAGMA wal_checkpoint(PASSIVE);")` invoked from maintenance paths.
**Data Shape:** Test grows the WAL to non-empty (100 rows), runs the checkpoint, and asserts the WAL file still EXISTS — passive checkpoints copy committed frames into the main DB but leave the file for concurrent readers.

### Decisive source
```c
/* Grow WAL beyond zero bytes via direct SQL. */
... INSERT INTO nodes(...) VALUES('p', 'Function', 'fn', 'p.module.fn_%d', 'f.c'); ...
/* WAL must exist and be non-empty before the checkpoint call. */
struct stat st_before; stat(wal_path, &st_before);
```

**Flow:** long-lived writers let WAL grow → maintenance calls PASSIVE checkpoint → pages migrate to main DB → readers never blocked, file persists → TRUNCATE mode is reserved for seal/publish paths where exclusivity is already held.
**Invariant:** Checkpoint mode must match lock ownership: PASSIVE for shared-lifetime maintenance, TRUNCATE only under the publish seal.
**Probe:** `tests/test_store_checkpoint.c:checkpoint_does_not_truncate_wal`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "wal_checkpoint", limit: 5 });
```

## Verdict
Adopt mode-appropriate checkpoints; adapt cadence; pair with seal-for-publish for the exclusive case.
