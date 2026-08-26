<!-- capsule-v2 -->
# Database manager — corruption-recovering SQLite with WAL, integrity checks, and rebuild-or-recreate

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent open a SQLite database that self-heals on corruption — configuring WAL/busy-timeout/FK, running integrity checks, migrating legacy schemas, and rebuilding-or-recreating the file while salvaging readable rows and backing up the corrupt set?

## DatabaseManager
**Path/Symbol:** `src/store/db.ts:DatabaseManager` (class, 140–1032); `getDb` (193–199), `open` (246–273), `openUnchecked` (275–295), `configureConnection` (297–308), `initializeSchema` (310–330), `withCorruptionRecovery` (212–222), `recoverFromCorruption` (228–241), `recoverDatabaseFile` (367–415), `rebuildDatabaseFromReadableRows` (543–579), `isCorruptionError` (169–183), `close` (996–1002). Schema in `src/store/schema.ts` (`SCHEMA_SQL`).
**Signature:** `new DatabaseManager(memoryDir, recoveryOptions?)`; `getDb() → DatabaseLike`; `withCorruptionRecovery<T>(op) → T`.
**Data Shape:** `DatabaseLike = { prepare, exec, close, pragma?, transaction? }`. Tables: `extension_metadata`, `sessions`, `session_files`, `messages` (+ `message_fts` FTS5), `memories` (+ `memory_fts` FTS5). FTS5 uses `content='…'` + `content_rowid` with INSERT/DELETE/UPDATE triggers. `DatabaseRecoveryResult = { strategy: 'rebuilt'|'recreated-empty'|'reused', backupPaths, recoveredRows?, error? }`.

### Decisive source
```ts
// configureConnection (297-308)
db.exec(`PRAGMA busy_timeout = ${SQLITE_BUSY_TIMEOUT_MS}`); // 5000
db.exec('PRAGMA journal_mode = WAL');
db.exec(`PRAGMA wal_autocheckpoint = ${SQLITE_WAL_AUTOCHECKPOINT_PAGES}`); // 1000
db.exec('PRAGMA journal_size_limit = 5242880');
db.exec('PRAGMA foreign_keys = ON');

// openUnchecked (275-295): integrity check before AND after schema init
if (existed) this.assertIntegrityOk(db, 'quick_check', 'before schema initialization');
this.configureConnection(db);
this.initializeSchema(db);
this.assertIntegrityOk(db, 'quick_check', 'after schema initialization');

// isCorruptionError (169-183): SQLITE_CORRUPT / SQLITE_NOTADB / malformed messages
// recoverDatabaseFile (367-415): acquire recovery lock via AtomicLockCoordinator, poll until deadline
//   → if currentDatabaseIsHealthy() reuse; else assertRecoveryCircuitClosed() then rebuild-or-recreate
// rebuildDatabaseFromReadableRows (543-579): copy recoverable rows per-table, rebuild FTS, verify FK+integrity, swap
// recoverDatabaseFileUnlocked (417-435): if file set exists try rebuild; else move files to backup + recreate-empty
```

**Flow:** (1) `getDb` lazily opens the DB, creating parent dirs. (2) `openUnchecked` runs `PRAGMA quick_check` before and after schema init, so a corrupt file is caught at open. (3) `initializeSchema` runs `SCHEMA_SQL`; on a legacy-schema error it adds missing columns and migrates the legacy `target CHECK` constraint to allow `failure`. (4) On any corruption error, `withCorruptionRecovery`/`open` acquire a recovery lock (via `AtomicLockCoordinator`), poll until a deadline, then either reuse a healthy DB or rebuild from readable rows (salvaging per-table data, rebuilding FTS, verifying FK + integrity) or move the corrupt file set to a `.corrupt-*` backup and recreate empty. (5) A recovery circuit (3 failures / 5 min) opens to stop repeated failed recovery. (6) `close` runs `PRAGMA wal_checkpoint(TRUNCATE)` then closes.

**Invariant:** a corrupt database is never silently returned — it is either repaired (rows salvaged) or quarantined and recreated empty, with the corrupt file set preserved as a backup; the recovery lease is token-fenced so a stolen lease aborts a destructive rename; FTS5 stays consistent with the content tables via triggers and an explicit rebuild after migration.

**Probe:** `tests/store/db.test.ts` — `should create all required tables` (:163), `should create FTS5 virtual tables` (:175), `should create triggers for FTS sync` (:186), `should migrate legacy memories table without category column` (:211), `should migrate legacy target CHECK constraint to allow failure entries` (:315), `repairs recoverable corruption on open and preserves readable rows` (:695), `quarantines unrecoverable files and recreates an empty database` (:736), `retries a corrupt operation once after self-healing` (:750), `should enable WAL mode for concurrent reads` (:846). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "DatabaseManager getDb recoverFromCorruption rebuildDatabaseFromReadableRows isCorruptionError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy open with pre/post integrity checks, the WAL + busy_timeout + FK connection config, the legacy-schema migration, the corruption-recovery lock + circuit breaker, and the rebuild-or-recreate with row salvage and backup retention. Adapt the table schema, the recovery timing constants, and the backup naming to the host. Omit the Bun compat ctor and the symlink-canonicalization of the DB path unless a target needs them.
