<!-- capsule-v2 -->
# File-hash change detection — what's the cheapest correct "did this file change?" test?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How are per-file hashes stored and compared for incremental indexing?

## sha256 + mtime_ns + size upsert with required-field validation
**Path/Symbol:** `src/store/store.c:cbm_store_upsert_file_hash` + tests/test_store_nodes.c:495 (`store_file_hash_crud`), 698 (`store_file_hash_upsert_rejects_null_required_fields`).
**Signature:** `int cbm_store_upsert_file_hash(cbm_store_t *s, const char *project, const char *rel_path, const char *sha256, long long mtime_ns, long long size);`
**Data Shape:** One row per (project, rel_path): sha256 hex, mtime_ns, size. Change = hash differs (mtime/size are advisory fast-paths). NULL/empty project or rel_path ⇒ ERR before SQL.

### Decisive source
```c
rc = cbm_store_upsert_file_hash(s, "test", "main.go", "abc123", 1000000, 512);
...
/* Update */
rc = cbm_store_upsert_file_hash(s, "test", "main.go", "def456", 2000000, 1024);
rc = cbm_store_get_file_hashes(s, "test", &hashes, &count);
ASSERT_EQ(count, 1);   /* still one row */
```

**Flow:** discovery hashes each candidate → compare against stored row → unchanged ⇒ skip extraction entirely → changed/new ⇒ re-extract → post-publish upsert refreshes rows.
**Invariant:** The HASH is authoritative; trusting mtime alone breaks on git operations that touch without changing content; validation must precede binding to keep error paths SQL-free.
**Probe:** `tests/test_store_nodes.c:store_file_hash_crud`, `store_file_hash_upsert_rejects_null_required_fields`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_upsert_file_hash", limit: 5 });
```

## Verdict
Adopt hash-authoritative change detection with metadata fast-paths; adapt hashing cost budget; validate inputs before the DB layer.
