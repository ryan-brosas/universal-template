<!-- capsule-v2 -->
# Lazy native binding — deferred better-sqlite3 load with ABI-mismatch recovery, Bun shim parity, and open-guard gating

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** A native SQLite module can fail to resolve (missing build), fail to load (ABI mismatch after a Node upgrade), or be ABSENT entirely (compiled Pi under Bun) — how do you defer, distinguish, recover, and gate?

## loadBetterSqlite3 + isBunRuntime
**Path/Symbol:** `src/store/sqlite-native.ts:loadBetterSqlite3`, `isBunRuntime`; consumer ladders `src/store/db.ts:DatabaseManager` ctor + `withCorruptionRecovery`; Bun shim `src/extension-root-migration.ts:createBunMigrationDatabaseCtor` (:37–97); lazy-load rationale (:101–113); open guard `src/index.ts:119-127` + `DatabaseManager.setOpenGuard`.
**Signature:** `loadBetterSqlite3() → DatabaseCtor (throws typed load errors)`; `isBunRuntime() → boolean`; `setOpenGuard(fn: (() => void) | null)`.
**Data Shape:** failure taxonomy surfaced to the user: module-not-found vs ABI/dlopen mismatch vs corruption — each with its own remedy string.

### Decisive source
```ts
// extension-root-migration.ts:101-113 — WHY the load is deferred:
/**
 * Resolved on first use, never at import time: this module is pulled in by
 * src/index.ts at extension load, and a module-scope native load turns any
 * SQLite resolve/ABI failure into "Failed to load extension" (issue #117).
 */
function getDatabaseCtor(): MigrationDatabaseCtor {
  if (!cachedDatabaseCtor) {
    cachedDatabaseCtor = isBunRuntime()
      ? createBunMigrationDatabaseCtor()      // bun:sqlite shim behind the SAME interface
      : (loadBetterSqlite3() as MigrationDatabaseCtor);
  }
  return cachedDatabaseCtor;
}

// Bun shim parity notes (37–97):
//   - busy_timeout via exec("PRAGMA busy_timeout = N") (no pragma method upstream)
//   - pragma(query): "=" form execs; read form prepares .get(); simple → first value
//   - backup(): NO online API → prepare("VACUUM INTO ?").run(dest)
//     (heartbeat callbacks only fire either side of it)

// index.ts:119-127 — migration-pending OPEN GUARD:
if (databaseMigrationPending) {
  dbManager.setOpenGuard(() => {
    if (databaseMigrationPending) throw new Error("Legacy sessions.db migration is pending");
  });
}
// …cleared on successful migration: dbManager.setOpenGuard(null)  (:176-179)
```

**Flow:** (1) import-time does NOT touch the native module — first USE constructs it; (2) runtime detection picks better-sqlite3 or the bun:sqlite shim implementing just the consumed slice; (3) ABI mismatches surface as an actionable error (one `npm rebuild`) instead of a generic extension-load failure (#117); (4) while a legacy-root DB migration is pending, every accidental `getDb()` throws through the open guard until the migration succeeds on session_start.
**Invariant:** deferral converts "extension cannot load" into "feature degrades with instructions"; the shim's job is INTERFACE PARITY for exactly the consumed methods — including emulating better-sqlite3's `pragma()` return-shape contract and substituting `VACUUM INTO` for the online backup API; the open guard makes a pending destructive migration impossible to race by failing closed.
**Probe:** `tests/store/sqlite-native.test.ts` + `tests/store/sqlite-lazy-load.test.ts` (deferred load, error classification, rebuild remedy text). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "loadBetterSqlite3 isBunRuntime setOpenGuard withCorruptionRecovery", limit: 5 })`

## Verdict
Adopt for any optional-native dependency in a plugin host. Adapt remedy commands. The porting traps: module-scope requires, missing `pragma()` return-shape emulation, and assuming an online-backup API exists under Bun (`VACUUM INTO` is the substitute).
