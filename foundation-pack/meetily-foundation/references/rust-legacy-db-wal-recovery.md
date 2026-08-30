<!-- capsule-v2 -->
# rust-legacy-db-wal-recovery — how does a Tauri app migrate a legacy SQLite file and survive orphaned WAL corruption?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the .db→.sqlite adoption order, the WAL-corruption recovery ladder, and the shutdown checkpoint contract?

## Copy-if-absent adoption + malformed/corrupt retry without WAL
**Path/Symbol:** `frontend/src-tauri/src/database/manager.rs:DatabaseManager::new / new_from_app_handle / cleanup` (:12-207).
**Signature:** `pub async fn new(tauri_db_path: &str, backend_db_path: &str) -> sqlx::Result<Self>`; `pub async fn cleanup(&self) -> Result<()>`.
**Data Shape:** Paths: app-data `meeting_minutes.sqlite` (sqlx/WAL) vs legacy `meeting_minutes.db` (old Python backend). Adoption ONLY when `.sqlite` is absent: copy `.db` → open pool → `sqlx::migrate!("./migrations")`. On connect failure whose message contains `"malformed"` or `"corrupt"`: DELETE `-wal` and `-shm` sidecars, retry `Self::new` ONCE; other errors propagate. Shutdown: `PRAGMA wal_checkpoint(TRUNCATE)` (non-fatal on error) then `pool.close()`.

### Decisive source
```rust
if !Path::new(tauri_db_path).exists() {
    if Path::new(backend_db_path).exists() {
        fs::copy(backend_db_path, tauri_db_path)...;
    } else {
        Sqlite::create_database(tauri_db_path).await?;
    }
}
...
if error_msg.contains("malformed") || error_msg.contains("corrupt") {
    // delete orphaned -wal/-shm, then retry Self::new once
```

**Flow:** first launch after upgrade copies the Python-era DB wholesale — table schemas are compatible by design (identical DDL, see initial_schema.sql), and sqlx migrations then add newer columns (backup columns etc.). The in-code comment warns users may delete the .sqlite to force re-adoption.
**Invariant:** Copy happens BEFORE pool creation and BEFORE migrations; never open the sqlite path first or the copy branch dies. Checkpoint uses TRUNCATE mode specifically so the WAL FILE IS DELETED (not just reused) — keeps portable data in one file for backup/restore.
**Probe:** `grep -c 'Removed orphaned' frontend/src-tauri/src/database/manager.rs` → `2` (battery T27); `grep -cF 'wal_checkpoint(TRUNCATE)' ...manager.rs` → `1` (T28); `grep -cF 'meeting_minutes.db' ...manager.rs` → `3` (T29).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "DatabaseManager wal_checkpoint legacy copy meeting_minutes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-before-open adoption, string-matched corruption retry, TRUNCATE checkpoint on exit; adapt paths/strings; omit Tauri dir resolution. Direct tests absent — behavior pinned via battery at pin.
