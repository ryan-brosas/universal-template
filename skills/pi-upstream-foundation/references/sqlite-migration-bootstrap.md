<!-- capsule-v2 -->
# SQLite migration bootstrap — how do you make embedded-SQLite schema setup idempotent and fail-closed without leaking a half-open connection?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** When a repository lazily opens its database on first use, how do you apply schema migrations so re-opening is a no-op, a failed migration leaves no partial state, and a failed setup never leaks the just-opened handle?

## Id-skip registry, one transaction per migration, close-on-failed-setup
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/migrations.ts:applyMigrations` (:35–49) with `loadMigrations` (:15–24); setup wrapper `src/sqlite/repo.ts:openDatabase` (:937–952).
**Signature:** `applyMigrations(db: SqliteDatabase): Promise<void>`; migrations are `{ id: string; order: number; sql: string }` loaded from files beside the module.
**Data Shape:** bookkeeping table `migrations(id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)` created with `IF NOT EXISTS` before any skip check; each unapplied migration's DDL plus its bookkeeping INSERT run inside ONE `db.transaction` (BEGIN IMMEDIATE in the node adapter).

### Decisive source
```ts
for (const migration of migrations) {
	if (applied.has(migration.id)) continue;
	db.transaction(() => {
		db.exec(migration.sql);
		sql`INSERT INTO migrations (id, applied_at) VALUES (${migration.id}, ${new Date().toISOString()})`.run(db);
	});
	applied.add(migration.id);
}
```
```ts
// repo.ts openDatabase — the only place a connection is created
const db = await this.options.sqlite.open(path);
try {
	configureSqliteDatabase(db);
	await applyMigrations(db);
	return db;
} catch (error) {
	db.close();
	throw error;
}
```

**Flow:** first operation → `getDatabase()` memoizes `openDatabase()` → resolve path → create parent dir → `sqlite.open` → configure pragmas → `applyMigrations` (ensure bookkeeping table → SELECT applied ids → for each unapplied migration: DDL + bookkeeping row in one transaction). A failure at configure OR migrate closes the handle before rethrowing. A failure AFTER setup (any later operation) does NOT close — the connection is retained until disposal, because the schema is intact and the WAL file remains valid for the next open.
**Invariant:** idempotence is id-set membership, not version comparison — re-running `applyMigrations` against an already-migrated database changes nothing. A failed migration rolls back atomically: no bookkeeping row, no partial tables. Setup failure ⇒ handle closed; operation failure ⇒ handle retained. The two failure classes must never be merged into one cleanup path.
**Probe:** `test/migrations.test.ts` — runs `applyMigrations` TWICE on one database, asserts exactly one `migrations` row (`001_initial.sql`) and the full table set via `sqlite_master`, plus PRAGMA assertions that superseded indexes/columns are absent (schema-shape witness, not just "it ran"). `test/repository.test.ts:180-192` ("closes the database when repository setup fails") uses a factory whose `exec` throws "setup failed" and asserts `counts.closes === 1` after the rejected `create`; :158-178 ("retains an opened database after a failed operation until disposal") asserts `closeCount === 0` after a failed insert and `=== 1` only after `[Symbol.asyncDispose]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(applyMigrations|openDatabase).*", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: id-skip registry with per-migration single-transaction application, and the two-class failure split (setup ⇒ close-and-rethrow; operation ⇒ retain-until-disposal). Adapt the migration list to your schema history; keep the bookkeeping INSERT inside the same transaction as the DDL or you get orphaned rows on crash. Omit version-number comparison entirely — it buys nothing over id membership and breaks when migrations are reordered. Caveat: MCP graph was not connected this pass; anchors verified by direct read at pin `4af9d21d`, and the double-apply + rollback + close-on-setup behavior was re-executed deterministically (node:sqlite transcription, probes P1.1–P1.3 GREEN).
