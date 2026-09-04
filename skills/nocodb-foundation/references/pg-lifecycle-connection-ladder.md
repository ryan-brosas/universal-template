<!-- capsule-v2 -->
|# pg lifecycle-connection ladder — how do testConnection, createDatabaseIfNotExists, and dropDatabase juggle throwaway `postgres`-db pools, and which idempotency guards prevent retry loops?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the pg client probe and provision databases it cannot currently reach, and what must a porter replicate about the temp-pool discipline?

## pg lifecycle-connection ladder
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts:testConnection` (:252–285), `createDatabaseIfNotExists` (:459–528) + `getEffectiveSchema` (:530–532), `dropDatabase` (:534–572), schema getter (:3625–3627); contrast `MysqlClient.createDatabaseIfNotExists` (:298–327).
**Signature:** all three build `deepClone(connectionConfig)` → swap `.connection.database = 'postgres'` → `knex({...clone, pool:{min:0,max:1}})` → use → `destroy()` in finally.
**Data Shape:** testConnection returns Result{code,message} where message = the ORIGINAL error (e1), never the fallback's.

### Decisive source
```ts
// testConnection :268–279 — the database-not-exist error is SUCCESS:
} catch (e) {
  if (!/^database "[\w\d_]+\" does not exist$/.test(e.message)) {
    result.code = -1;
    result.message = e1.message;   // original failure wins; fallback noise suppressed
  }
} finally { await tempSqlClient.destroy(); }
// (fallback against 'postgres' db distinguishes bad-credentials from missing-database)

// createDatabaseIfNotExists :500–514 — why schemaExists is probed instead of IF NOT EXISTS:
// Check schemaExists because `CREATE SCHEMA IF NOT EXISTS` requires permissions of `CREATE ON DATABASE`
const schemaExists = !!(await raw(`SELECT schema_name FROM information_schema.schemata WHERE schema_name = ?`,[schemaName])).rows?.[0];
if (!schemaExists) await this.sqlClient.raw(`CREATE SCHEMA IF NOT EXISTS ??`, [schemaName]);
// db-exists probe itself has a FALLBACK LADDER: try temp('postgres') pool first,
// catch → retry the same pg_database SELECT on THIS.sqlClient (:470–492).

// dropDatabase :552–557 — evict every other backend BEFORE dropping:
`ALTER DATABASE ?? WITH CONNECTION LIMIT 0;
 SELECT pg_terminate_backend(sa.pid) FROM pg_stat_activity sa
 WHERE sa.pid <> pg_backend_pid() AND sa.datname = ?;`
// then destroy() the ORIGINAL pool and REASSIGN this.sqlClient = tempSqlClient.
```

**Flow:** test: primary SELECT 1+1 fails → clone config to postgres db with pool max 1 → retry → only "does not exist" counts as passable. create: probe pg_database via temp pool (falling back to own pool when even that fails) → CREATE DATABASE IF ABSENT (`ENCODING 'UTF8'`) → probe schemata for effective schema (`args.schema || searchPath[0] || 'public'`) → create if missing → destroy temp in finally. drop: kill connections + connection-limit 0 → DROP DATABASE → pool swap so subsequent ops don't resurrect the dead handle.

**Invariant:** (1) Temp pools are ALWAYS min:0/max:1 and ALWAYS destroyed in finally — reusing or leaking them pins connections on the meta DB. (2) The "database does not exist" regex is a deliberate success path: failing closed here makes freshly-provisioned hosts untestable. (3) Schema creation is gated on an explicit EXISTS probe because IF NOT EXISTS demands CREATE ON DATABASE — a permission restricted-role users have; silently switching to plain IF NOT EXISTS breaks shared-credential provisioning. (4) dropDatabase swallows its errors (no rethrow) — callers treat drop as best-effort cleanup, unlike create. (5) MySQL's twin deletes `.connection.database` instead of pointing at 'postgres' (no sentinel DB exists there).

**Probe:** runner BLOCKED (no upstream spec imports PgClient) → deterministic probes at pin: `sed -n '270,278p' packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` shows regex+e1.message verbatim; `grep -n "CREATE ON DATABASE" packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` resolves the :502 comment; `grep -c "pg_terminate_backend" packages/nocodb/src/db/sql-client/lib/pg/PgClient.ts` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "PgClient testConnection createDatabaseIfNotExists dropDatabase pg_terminate_backend", limit: 10 });
```

## Verdict
Adopt the throwaway-postgres-pool pattern with min0/max1+finally-destroy, the does-not-exist success carve-out, and the exists-probe-before-CREATE-SCHEMA permission workaround; adapt sentinel-db name per dialect; omit the pool-swap behavior unless your host also drops live handles mid-flight.
