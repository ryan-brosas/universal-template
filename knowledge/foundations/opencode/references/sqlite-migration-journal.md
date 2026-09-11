<!-- capsule-v2 -->
# SQLite migration journal — how do you migrate a DB that predates your journal and refuse foreign databases?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does a TypeScript-migration runner initialize a fresh DB, adopt an install that used a different migration journal, and refuse to initialize over an unrelated database?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/database/migration.ts`: `apply` (:14-37), `applyOnly` (:39-75); `packages/core/src/database/migration.gen.ts` (:1-44, 38 ordered dynamic imports).
**Signature:** `apply(db) => Effect<void, unknown>` (under `Semaphore.makeUnsafe(1)`); `applyOnly(db, input: Migration[]) => Effect<void, unknown>`; `Migration = { id: string, up: (tx) => Effect<void, unknown> }`.
**Data Shape:** journal table `migration(id TEXT PRIMARY KEY, time_completed INTEGER NOT NULL)`; legacy journal `__drizzle_migrations(name ...)`.

### Decisive source
```ts
const tables = yield* db.all<{ name: string }>(
  sql`SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'`,
)
if (tables.some((table) => table.name === "session")) return yield* applyOnly(db, migrations)
if (tables.length > 0) return yield* Effect.die("Database is not empty and has no session table")
```
```ts
if (completed.size === 0) {
  // Existing installs used Drizzle's migration journal. Seed the new
  // journal once so TypeScript migrations don't replay old SQL.
  if (yield* db.get(sql`SELECT name FROM sqlite_master WHERE type = 'table' AND name = ${"__drizzle_migrations"}`)) {
    yield* db.run(sql`
      INSERT OR IGNORE INTO ${sql.identifier("migration")} (id, time_completed)
      SELECT name, ${Date.now()}
      FROM ${sql.identifier("__drizzle_migrations")}
      WHERE name IS NOT NULL
    `)
```

**Flow:** `apply` lists non-sqlite_ tables → a `session` table means an existing install: run `applyOnly(migrations)` → ANY other tables without `session` DIE (refuses to initialize over a foreign DB) → empty DB: one transaction creates the schema + journal + inserts all 38 migration ids as done. `applyOnly` (the incremental path): create journal IF NOT EXISTS → read completed ids → if EMPTY, import legacy `__drizzle_migrations` names ONCE (so TS migrations never replay old SQL) → for each pending migration: one transaction = `migration.up(tx)` + journal insert. `migration.gen.ts` orders all 38 migration modules via dynamic imports.
**Invariant:** the module-level semaphore serializes concurrent `apply` on one DB (test: two concurrent `layerFromPath` builds both succeed); each migration runs in exactly one transaction with its journal row, so a failed `up` leaves no half-applied step; the drizzle import happens only when the journal is empty, never twice.
**Probe:** `packages/core/test/database-migration.test.ts` (644L, 15 tests: concurrent init serialization, empty-DB full apply with table+index assertions, foreign-DB die, drizzle import, "does not replay a migrated session metadata column", temporary replacement-id acceptance, per-migration backfills — usage columns, Windows path normalization, event-sourced reset, V1 restart).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "DatabaseMigration apply applyOnly __drizzle_migrations journal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-table check with the foreign-DB die, the one-shot legacy-journal import gated on an empty journal, and per-migration transactional application. Adapt the sentinel table name and journal schema to your domain. Omit the drizzle import branch if your installs never predate the journal. Coverage caveat: `applyOnly` has no src callers outside `apply` at this pin (grep-verified) — it exists for tests and future partial application; the 38 migration bodies themselves are data, not cited.
