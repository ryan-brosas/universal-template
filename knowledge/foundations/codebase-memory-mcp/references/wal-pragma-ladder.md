<!-- capsule-v2 -->
# WAL pragma ladder — how do you share a SQLite graph DB across processes without SIGBUS or a starved WAL?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Which pragmas apply to which connection mode, and why is TRUNCATE checkpoint forbidden on shared paths?

## Three-arm pragma configuration
**Path/Symbol:** `src/store/store.c:configure_pragmas` (415–483).
**Signature:** `static int configure_pragmas(cbm_store_t *s, bool in_memory, bool read_only);`
**Data Shape:** `in_memory` → `synchronous=OFF`, no journal file; `read_only` → ONLY non-writing pragmas (`foreign_keys=ON`, `temp_store=MEMORY`, `busy_timeout=10000`, `mmap_size`); else writer arm → `busy_timeout=10000` + `journal_mode=WAL` + best-effort PASSIVE checkpoint (crash-WAL recovery) + `synchronous=NORMAL` + `journal_size_limit=268435456`.

### Decisive source
```c
/* Shared/live paths do NOT use a TRUNCATE checkpoint: truncating the WAL
 * to zero can raise SIGBUS in a sibling process that has the DB mmap'd
 * on macOS. Exclusive staging publication seals separately below. */
(void)sqlite3_exec(s->db, "PRAGMA wal_checkpoint(PASSIVE)", NULL, NULL, NULL);
rc = exec_sql(s, "PRAGMA journal_size_limit = 268435456;"); /* 256 MiB */
```

**Flow:** open → configure_pragmas by mode → writers run under WAL with busy_timeout 10s → checkpoints are always PASSIVE on live DBs → journal_size_limit reclaims only after abnormal growth (healthy WAL ≈ 4 MiB vs 1000-page autocheckpoint).
**Invariant:** Read-only connections run zero writing pragmas (they would mutate the DB every query and fail on RO filesystems); TRUNCATE checkpoints exist ONLY inside exclusive staging publication (`cbm_store_seal_for_atomic_publish`) where no sibling can hold an mmap.
**Probe:** `tests/test_store_pragmas.c:journal_size_limit_bounds_wal_issue1083` asserts `journal_size_limit == 268435456` and `tests/test_store_checkpoint.c:checkpoint_does_not_truncate_wal` pins PASSIVE-only behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "configure_pragmas", limit: 5 });
```

## Verdict
Adopt the mode-partitioned pragma ladder and the "PASSIVE everywhere except sealed staging" rule plus the 256 MiB starvation bound; adapt the mmap-size env override (`CBM_SQLITE_MMAP_SIZE`, default 64 MiB, negative→0) to your env-var conventions; omit the macOS SIGBUS war story if your platform never mmaps concurrently.
