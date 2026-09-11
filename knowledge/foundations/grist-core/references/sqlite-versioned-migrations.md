<!-- capsule-v2 -->
# Versioned SQLite migrations — what is the contract between create(), the migrations array, and a failed migration?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you keep `CREATE TABLE` truth and historical migrations in one file so every old database converges to the same schema — without down-migrations or a migration table?

## create()+migrations twin-list with user_version, backup-before-migrate, open-anyway-on-failure
**Path/Symbol:** `app/server/lib/SQLiteDB.ts:SQLiteDB.openDB` (171–201), `_migrate` (555–597), `_initNewDB` (540–546), `_reportSchemaDiscrepancies` (599–609), `SchemaInfo` (103–120).
**Signature:** `static async openDB(dbPath: string, schemaInfo: SchemaInfo, mode?: OpenMode, hooks?: MigrationHooks): Promise<SQLiteDB>`; `SchemaInfo = { create: DBFunc; migrations: readonly DBFunc[] }`.
**Data Shape:** schema version lives in SQLite's `PRAGMA user_version`; target version = `migrations.length`; backup file ``${filePath}.${YYYY-MM-DD}.V${version}{NUM}.bak``; `MigrationHooks = { beforeMigration?(cur,new), afterMigration?(new,success) }`.

### Decisive source
```ts
// The very first migration should normally be identical to the original version of create().
// I.e. initially SchemaInfo should be { create: X, migrations: [X] } ...
// Don't go for code reuse here. ... Keeping the unchanged copy of X is important as a
// reference to see that X + Y produces the same DB as X2.            (SchemaInfo doc)
if (userVersion === 0 && (await isGristEmpty(db))) {
  await db._initNewDB(schemaInfo);              // fresh DB: run create(), stamp targetVer
} else if (mode === OpenMode.OPEN_READONLY) {   // never migrate read-only — record error instead
  if (userVersion < targetVer) db._migrationError = new Error(`needs migration but is readonly`);
} else {
  try { db._migrationBackupPath = await db._migrate(userVersion, schemaInfo, hooks); }
  catch (err) { db._migrationError = err; }     // FAILED MIGRATION OPENS ANYWAY
}
...
backupPath = await createBackupFile(this._dbPath, actualVer);
await this.execTransaction(async () => {
  for (const versionNum of versions) await schemaInfo.migrations[versionNum](this);
  await this.exec(`PRAGMA user_version = ${targetVer}`);   // data + version flip in ONE tx
});
```

**Flow:** open raw → read `user_version` → empty-and-unversioned ⇒ init new DB inside one transaction → otherwise compare versions: behind ⇒ copy file to dated `.V{n}.bak`, run all missing migrations + version bump in ONE transaction, `VACUUM` outside it, delete the backup only on failure; ahead-of-code or readonly-behind ⇒ warn/record `migrationError` but still return an open handle → always finish with `_reportSchemaDiscrepancies`, which materializes `create()` into a throwaway in-memory DB, caches its metadata by function identity, and diffs real tables against expectation with warnings.
**Invariant:** migration entries are append-only history — editing an old migration silently breaks every DB below that version; `create()` and the first migration start as literal copies and only `create()` evolves; a failed migration leaves the file byte-identical (transaction rollback) AND removes the useless backup, surfacing failure as `db.migrationError` rather than refusing service; unversioned non-empty DBs (pre-module era) are driven through ALL migrations starting at 1, so migration #1 must normalize any legacy layout.
**Probe:** `test/server/lib/SQLiteDB.ts::"should apply migrations, with backup, if needed"` (:136), `::"should migrate across multiple versions"` (:212), `::"should migrate DBs created without versioning"` (:261), `::"should skip migration backup on migration failure"` (:300), `::"should warn if DB is incorrect, incl after migrations"` (:345).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "SQLiteDB openDB _migrate SchemaInfo", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the twin-list discipline (`create()` + frozen migration copies), single-transaction migrate+bump, dated pre-migration backup with failure cleanup, and open-anyway-with-recorded-error posture for any embedded/local database (SQLite, DuckDB, IndexedDB schemas). Adapt the version store (`user_version` pragma vs a meta table), backup naming, and hook surface to host. Omit the ATTACH limiting and vacuum plumbing unless your engine shares those footguns.
