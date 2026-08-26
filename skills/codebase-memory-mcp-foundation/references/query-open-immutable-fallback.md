<!-- capsule-v2 -->
# Store open modes — why must read queries never mutate the DB file?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do I open the graph DB for a read-only tool call without mutating it, creating a ghost file, or SIGBUS-ing sibling processes?

## Query-only open with immutable fallback
**Path/Symbol:** `src/store/store.c:cbm_store_open_path_query` (837–923).
**Signature:** `cbm_store_t *cbm_store_open_path_query(const char *db_path);`
**Data Shape:** Returns an opaque store or NULL (missing DB → NULL, never creates). Internally: READONLY sqlite3 handle + non-writing pragmas only (`foreign_keys`, `temp_store=MEMORY`, `busy_timeout=10000`, `mmap_size`).

### Decisive source
```c
int rc = sqlite3_open_v2(open_path, &s->db, SQLITE_OPEN_READONLY, NULL);
if (rc == SQLITE_OK) {
    /* Force first DB access so a read-only-FS WAL failure surfaces now. */
    if (sqlite3_exec(s->db, "SELECT 1 FROM sqlite_master LIMIT 1;", ...) != SQLITE_OK) { ... rc = SQLITE_CANTOPEN; }
}
if (rc != SQLITE_OK) {
    ...
    if (!cbm_file_exists(db_path)) { free(s); return NULL; }  /* no ghost .db */
    build_immutable_uri(db_path, uri, sizeof(uri));           /* file:...?immutable=1 */
    rc = sqlite3_open_v2(uri, &s->db, SQLITE_OPEN_READONLY | SQLITE_OPEN_URI, NULL);
}
```

**Flow:** plain READONLY open → probe-read to force lazy WAL/-shm failure early → if probe failed AND file exists, retry once via percent-encoded `file:` URI with `immutable=1` (bypasses WAL+locks, reads main file directly) → missing file returns NULL immediately.
**Invariant:** A read query must never mutate the DB (no WAL write-pragmas on read paths — the old READWRITE open did) and a missing project must return NULL without creating anything.
**Probe:** `tests/test_store_pragmas.c` (`store_open_with_mmap_disabled`, `mmap_size_*`) plus `tests/repro/repro_issue557.c`; writer/reader pragma split is pinned by `configure_pragmas` in-memory/read_only/write three-arm test coverage in test_store_pragmas.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_open_path_query", limit: 5 });
```

## Verdict
Adopt the three-mode split (`open_path` RW/WAL create, `open_path_existing` RW no-create, `open_path_query` READONLY-with-immutable-fallback) and the "probe before fallback" trick; adapt the immutable-URI builder's Windows drive-letter normalization to your host; omit the mimalloc-backed page-cache slab rationale if you have no allocator instrumentation.
