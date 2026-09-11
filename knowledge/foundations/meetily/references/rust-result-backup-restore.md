<!-- capsule-v2 -->
# rust-result-backup-restore — how does regeneration avoid destroying the previous summary on failure or cancel?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the exact SQL lifecycle of `result_backup` across create/reset, completed, failed and cancelled transitions?

## Backup-on-reset, restore-on-fail/cancel, clear-on-complete
**Path/Symbol:** `frontend/src-tauri/src/database/repositories/summary.rs:SummaryProcessesRepository` (:85-220); migration `20251101000000_add_summary_backup.sql`.
**Signature:** `pub async fn create_or_reset_process(pool: &SqlitePool, meeting_id: &str)`; `update_process_completed(pool, meeting_id, result: Value, chunk_count: i64, processing_time: f64)`; `update_process_failed(pool, meeting_id, error: &str)`; `update_process_cancelled(pool, meeting_id)`.
**Data Shape:** `summary_processes` gains `result_backup TEXT` + `result_backup_timestamp TEXT`. Reset (upsert): existing `result` is COPIED to `result_backup`, row set PENDING with `result = result` (kept visible during regeneration), error NULL. Completed: write new result, clear both backup columns. Failed/Cancelled: `result = COALESCE(result_backup, result)` then clear backups; cancelled also pins `error = 'Generation was cancelled by user'`.

### Decisive source
```sql
ON CONFLICT(meeting_id) DO UPDATE SET
    status = 'PENDING', ...
    result_backup = result,
    result_backup_timestamp = excluded.updated_at,
    result = result,
    error = NULL
...
-- failed / cancelled:
SET status = 'failed', ..., result = COALESCE(result_backup, result),
    result_backup = NULL, result_backup_timestamp = NULL
```

**Flow:** UI "regenerate" ⇒ create_or_reset (old summary preserved but stale-visible) ⇒ background run ⇒ completed overwrites+clears OR failed/cancelled restores. The user NEVER sees a lost summary from a failed regeneration.
**Invariant:** The upsert requires BOTH columns to exist (migration 20251101000000 must run before this code path); `create_or_reset` is called by the COMMAND handler BEFORE spawning the background task, so a spawn failure still leaves the old summary restorable. Note the deliberate `result = result` self-assign keeps prior content readable while status=PENDING.
**Probe:** `grep -cF 'COALESCE(result_backup, result)' frontend/src-tauri/src/database/repositories/summary.rs` → `2` (battery T23); `grep -cF 'result_backup = result,' ...summary.rs` → `1` (T24); `grep -c 'result_backup = NULL' ...summary.rs` → `3` (T25).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "result_backup update_process_cancelled create_or_reset_process COALESCE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-transition backup lifecycle verbatim (it is pure SQL + state discipline); adapt table names; omit nothing. Direct tests absent for repo layer — behavior pinned via battery + schema migration read at pin.
