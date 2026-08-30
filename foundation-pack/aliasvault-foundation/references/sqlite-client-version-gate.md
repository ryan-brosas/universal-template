<!-- capsule-v2 -->
# SQLite client transaction + version gate — how does the extension guard an out-of-date vault before touching it?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How is the client vault's schema version read, compared, and enforced?

## Migration-history version probe
**Path/Symbol:** `apps/browser-extension/src/utils/SqliteClient.ts:318-366` (`getDatabaseVersion`), :382-392 (`hasPendingMigrations`), :277-302 (`executeRaw` statement filtering), :135-193 (transaction trio).
**Signature:** `async getDatabaseVersion(): Promise<VaultVersion>` — reads `SELECT MigrationId FROM __EFMigrationsHistory ORDER BY MigrationId DESC LIMIT 1`.
**Data Shape:** MigrationIds embed the semver (`20251213111207_1.7.0-FieldBasedDataModelUpdate`); `extractVersionFromMigrationId` parses it; `checkVersionCompatibility` decides support; incompatible ⇒ throw typed `VaultVersionIncompatibleError` with i18n message `common.errors.browserExtensionOutdated`.

### Decisive source
```ts
if (!compatibilityResult.isCompatible) {
  const errorMessage = await t('common.errors.browserExtensionOutdated');
  throw new VaultVersionIncompatibleError(errorMessage);
}
if (compatibilityResult.isKnownVersion && compatibilityResult.clientVersion) {
  return compatibilityResult.clientVersion;
}
// Unknown-but-backwards-compatible:
return { revision: latestClientVersion.revision, version: databaseVersion,
  description: `Unknown version ${databaseVersion} (backwards compatible)`, ... };
```
```ts
// executeRaw strips transaction control statements — callers own BEGIN/COMMIT:
if (trimmedStatement.toUpperCase().startsWith('BEGIN TRANSACTION') ||
    trimmedStatement.toUpperCase().startsWith('COMMIT') ||
    trimmedStatement.toUpperCase().startsWith('ROLLBACK')) { continue; }
```

**Flow:** initialize from base64 → repositories lazily built and RESET on every re-initialization (:121-125) → version probe on open; unknown-newer versions are tolerated with a synthesized "backwards compatible" descriptor while older-than-floor throws → migrations applied inside explicit beginTransaction/commit/rollback pairs where executeRaw refuses to touch control statements.
**Invariants:** (1) Transaction state is a boolean latch — double-begin or commit-without-begin throws instead of silently nesting. (2) Raw SQL splitting is naive-on-purpose (`query.split(';')`) but control statements are filtered so migration scripts can't bypass the latch. (3) Repository caches are invalidated whenever a new database blob is loaded — stale repository handles would read the wrong DB. (4) Forward compatibility: unknown HIGHER versions pass with a marker; only known-incompatible versions hard-fail.
**Probe:** `grep -c '__EFMigrationsHistory' apps/browser-extension/src/utils/SqliteClient.ts` → `1`; `grep -c "toUpperCase().startsWith('COMMIT')" apps/browser-extension/src/utils/SqliteClient.ts` → `1`; `grep -c 'this._items = null' apps/browser-extension/src/utils/SqliteClient.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "checkVersionCompatibility", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt EF-migrations-history-as-version-source + forward-compatible gate + control-statement-filtered raw executor; adapt to your migration tracker; omit sql.js specifics. Source confirmed at pin `95903e92`; jest suite not runnable here.
