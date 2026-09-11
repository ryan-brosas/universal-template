<!-- capsule-v2 -->
# Session storage write serialization — how do concurrent processes share one SQLite session store without corrupting init or IDs?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How do I make a multi-process SQLite-backed session store whose first-run schema creation, migrations, and ID allocation are all race-safe?

## Write serialization kernel
**Path/Symbol:** `crates/goose/src/session/session_manager.rs` : `SessionStorage.create_pool/pool/create_schema/create_session` (896-945, 947-1091, 1565-1608).
**Signature:** `async fn pool(&self) -> Result<&Pool<Sqlite>>` / `async fn create_session(&self, working_dir: PathBuf, name: String, session_type: SessionType, goose_mode: GooseMode) -> Result<Session>`.
**Data Shape:** One process-global store: `static SESSION_STORAGE: LazyLock<Arc<SessionStorage>>` over `Paths::data_dir()`; `SessionStorage { pool: Pool<Sqlite>, initialized: tokio::sync::OnceCell<()>, session_dir, action_required }`. Pool is `connect_lazy_with(SqliteConnectOptions … .foreign_keys(true).busy_timeout(30s).journal_mode(Wal))`.

### Decisive source
```rust
// create_schema — run under `BEGIN IMMEDIATE` so SQLite serializes
// writers across processes. Combined with `IF NOT EXISTS` on every
// DDL statement and `INSERT OR IGNORE` on the bootstrap version
// row, this makes init safe under concurrent first-run startup —
// the previous flow:
//   SELECT EXISTS('schema_version') → false
//   CREATE TABLE schema_version (...)
// raced when two processes both saw "doesn't exist" ...
let mut tx = pool.begin_with("BEGIN IMMEDIATE").await?;
```
```sql
INSERT INTO sessions (id, ...) VALUES (
    ? || '_' || CAST(COALESCE((
        SELECT MAX(CAST(SUBSTR(id, 10) AS INTEGER)) FROM sessions WHERE id LIKE ? || '_%'
    ), 0) + 1 AS TEXT), ...)
RETURNING *
```

**Flow:** lazy first use → OnceCell checks `schema_version` table → exists: sequential `apply_migration(v)`+version bump for each missing version inside ONE IMMEDIATE tx; absent: `create_schema` then best-effort `import_legacy` (failures are warn-only, never block startup) → every later mutation (`create_session`, `apply_update`, `add_message`, `replace_conversation_inner`, `delete_session`, `record_usage_metrics`, `update_message_metadata`, `update_tool_request_meta_by_message_id`, `truncate_conversation_from_message`, migration runs) opens its own `BEGIN IMMEDIATE` transaction.
**Invariant:** Every read-modify-write against the DB happens inside `BEGIN IMMEDIATE`; no DEFERRED transaction ever upgrades SHARED→RESERVED mid-flight. Session IDs are date-sequential `YYYYMMDD_N` where N = MAX(existing N for today)+1 computed in the same IMMEDIATE tx as the INSERT.
**Probe:** `crates/goose/src/session/session_manager.rs` tests `test_begin_immediate_prevents_lock_upgrade_deadlock` (BEGIN DEFERRED races produce SQLITE_BUSY; BEGIN IMMEDIATE all-Ok) and `test_concurrent_session_creation` (10 concurrent creates, distinct IDs). Run: `cargo test -p goose --lib session::session_manager`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "BEGIN IMMEDIATE create_schema concurrent migration session storage lock upgrade", limit: 8, fields: ["lines"] });
```

## Verdict
Adopt the contract: WAL + busy-timeout pool, one global store handle, IMMEDIATE-only writes, idempotent guarded DDL migrations with a version table, and allocate human-readable sequential IDs atomically in SQL. Adapt the ID format and legacy-import step to your host. Omit goose's ActionRequiredManager coupling and telemetry emit.
