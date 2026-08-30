<!-- capsule-v2 -->
# Shared DB connection & migration preamble — how does a process own exactly one TypeORM DataSource, and what pragmas must wrap schema work?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How are home-server DB connections shared, tuned, and safely migrated across sqlite and postgres?

## dbUtils connection/migration kit
**Path/Symbol:** `app/server/lib/dbUtils.ts:getOrCreateConnection` (211-245), `createConnection` (190-203), `withSqliteForeignKeyConstraintDisabled` (266-276), `getMigrations` (148-171), `getTypeORMSettings` (285-329).
**Signature:** `getOrCreateConnection(): Promise<DataSource>` (mutex-guarded module singleton); `createConnection(settings: DataSourceOptions): Promise<DataSource>`; `withSqliteForeignKeyConstraintDisabled<T>(dataSource, cb): Promise<T>`; `getMigrations(dataSource): Promise<{migrationsInDb, migrationsInCode, pendingMigrations}>`.
**Data Shape:** Env-driven settings: `TYPEORM_TYPE` (default sqlite), `TYPEORM_DATABASE` (default landing.db), `TYPEORM_NAME` (default "default"), `TYPEORM_REDIS_URL` (query cache), `TYPEORM_EXTRA` (JSON deep override). Spread order: base config → redis cache → caller override → `JSON.parse(TYPEORM_EXTRA)` (last wins).

### Decisive source
```ts
let gristDataSource: DataSource | null = null;
const connectionMutex = new Mutex();
export async function getOrCreateConnection(): Promise<DataSource> {
  return connectionMutex.runExclusive(async () => {
    // If multiple servers are started within the same process, we share the
    // database connection. This saves locking trouble with Sqlite.
    if (!gristDataSource?.isInitialized) {
      let settings = getTypeORMSettings();
      if (settings.type === "postgres") {
        settings = getTypeORMSettings({ extra: { options: "-c jit=off" } }); // JIT pathology
      }
      gristDataSource = await createConnection(settings);
    }
    return gristDataSource;
  });
}
export async function withSqliteForeignKeyConstraintDisabled<T>(dataSource, cb): Promise<T> {
  const sqlite = getDatabaseType(dataSource) === "sqlite";
  // disable OUTSIDE any transaction, or it has no effect
  if (sqlite) { await dataSource.query("PRAGMA foreign_keys = OFF;"); }
  try { return await cb(); }
  finally { if (sqlite) { await dataSource.query("PRAGMA foreign_keys = ON;"); } }
}
```

**Flow:** All consumers funnel through the mutex-guarded singleton — one initialized DataSource per process, shared by every server instance in it (deliberate: avoids sqlite cross-handle locking). Postgres sessions inject `-c jit=off` via libpq `options` to dodge a JIT mis-cost on one hot query. `createConnection` sets `PRAGMA busy_timeout = 3000` AFTER initialize on sqlite (tolerates test interference; harmless for postgres/single-process). Migrations (`runMigrations`/`undoLastMigration`) always run inside the FK-disabled wrapper because typeorm's sqlite strategy copies+rebuilds each table per schema change; `transaction: "all"` batches them. `getMigrations` diffs DB vs code by name — a failed `select name from migrations` counts as ZERO-run only when the error is `QueryFailedError` mentioning "migrations" (sqlite and postgres report absence differently). `updateDb` = migrations + `synchronizeProducts`.
**Invariant:** `PRAGMA foreign_keys` toggling MUST happen outside any open transaction or it silently no-ops; busy_timeout is set post-initialize; `synchronize:false, migrationsRun:false` are pinned so schema changes only ever happen through the audited migration path. Connection creation is single-flighted — a second concurrent starter must receive the SAME DataSource, not race a duplicate.
**Probe:** No dedicated unit file (coverage caveat); exercised across gen-server test suites that boot via updateDb. Deterministic anchors: `grep -n "busy_timeout\|foreign_keys = OFF" app/server/lib/dbUtils.ts` → :200/:270; `grep -n "jit=off" app/server/lib/dbUtils.ts` → :238.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "getOrCreateConnection withSqliteForeignKeyConstraintDisabled", limit: 5 });
```
## Verdict
Adopt the mutex-singleton connection owner, post-init busy_timeout, out-of-transaction FK disabling around sqlite migrations, and name-diff migration summaries with dialect-tolerant zero-state detection; adapt env vocabulary and ORM; omit the postgres JIT anecdote unless you hit the same planner pathology.
