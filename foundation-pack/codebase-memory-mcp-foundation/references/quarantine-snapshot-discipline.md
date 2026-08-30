<!-- capsule-v2 -->
# Quarantine snapshot discipline — what must happen to DB+WAL bytes BEFORE a corrupt store is deleted?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you quarantine a database so no committed page is ever lost?

## Snapshot publish (db + wal) before delete, under guard
**Path/Symbol:** `src/mcp/mcp.c` corrupt-store cleanup + tests/test_mcp.c:6715 (`tool_corrupt_store_cleanup_publishes_complete_wal_snapshot_before_delete`), 6573 (`preserves_existing_backup_and_uses_unique_name`), 6639 (`publish_failure_preserves_db_and_wal`), 6248/6330 (guard balance/denial).
**Signature:** quarantine flow: acquire project mutation guard → read db+wal byte snapshots → publish backup copy → verify → only then remove originals; test hooks deny at named steps.
**Data Shape:** Backup naming unique per attempt preserving any EXISTING backup (never overwrite the previous crime scene); denial at after_snapshot_publish ⇒ db+wal byte-identical to before.

### Decisive source
```c
long db_len = 0; long wal_len = 0;
unsigned char *db_before = mcp_read_file_bytes(db_path, &db_len);
unsigned char *wal_before = mcp_read_file_bytes(wal_path, &wal_len);
...
bool db_unchanged = mcp_file_matches_snapshot(db_path, db_before, db_len);
```

**Flow:** guard begin → snapshot both files → write backup → hook point → originals removed only after verified publish; failure ⇒ restore/leave untouched.
**Invariant:** WAL contains committed-but-not-checkpointed pages — deleting a "corrupt" DB without its WAL loses real data; backups are append-only artifacts.
**Probe:** the four named tests plus `tool_corrupt_store_cleanup_rechecks_generation_after_guard_wait`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "quarantine", limit: 5 });
```

## Verdict
Adopt snapshot-verify-delete for destructive recovery of any multi-file artifact; adapt naming; keep guards balanced even on denial paths.
