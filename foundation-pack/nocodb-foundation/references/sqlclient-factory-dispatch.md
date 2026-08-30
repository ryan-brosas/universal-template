<!-- capsule-v2 -->
|# sql-client factory dispatch — how does one connection config choose a dialect client, and what must happen before any client is constructed?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Where is the dialect→client mapping decided, which vendor variants fork off the same base class, and why does the default export differ from the named class?

## sql-client factory dispatch
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/SqlClientFactory.ts:SqlClientFactory.create` (:10–36) + default export (:38–44); consumers: `utils/common/NcConnectionMgrv2.ts:getSqlClient` and `db/sql-migrator/lib/KnexMigratorv2.ts`, `db/sql-mgr/v2/SqlMgrv2.ts`.
**Signature:** `static create(connectionConfig): SqlClient` (sync); default-export `create(connectionConfig)` is ASYNC because it awaits `resolveSslFileConfig(connectionConfig)` first.
**Data Shape:** input `{ client: 'mysql'|'mysql2'|'sqlite3'|'pg', connection?, meta?: { dbtype?: 'tidb'|'vitess'|'yugabyte' }, pool?, knex? }`; returns MySqlClient/SqliteClient/PgClient or a vendor subclass.

### Decisive source
```ts
// :11–14 — defaults injected BEFORE dispatch; callers may omit meta/pool entirely
connectionConfig.meta = connectionConfig.meta || {};
connectionConfig.pool = connectionConfig.pool || { min: 0, max: 5 };
// :15–30 — two-level dispatch: wire protocol FIRST, then dbtype variant
if (connectionConfig.client === 'mysql' || connectionConfig.client === 'mysql2') {
  if (connectionConfig.meta.dbtype === 'tidb')    return new TidbClient(connectionConfig);
  if (connectionConfig.meta.dbtype === 'vitess')  return new VitessClient(connectionConfig);
  return new MySqlClient(connectionConfig);
} else if (connectionConfig.client === 'sqlite3') return new SqliteClient(connectionConfig);
else if (connectionConfig.client === 'pg') {
  if (connectionConfig.meta.dbtype === 'yugabyte') return new YugabyteClient(connectionConfig);
  return new PgClient(connectionConfig);
}
NcError.notImplemented(`Database ${...meta.dbtype} is not supported`);
```
```ts
// NcConnectionMgrv2.getSqlClient — the PRODUCTION path reuses an existing knex handle:
return SqlClientFactory.create({ knex, ...(await source.getConnectionConfig()) });
// → KnexClient ctor :153–162 honors connectionConfig.knex instead of opening its own pool.
```

**Flow:** resolve SSL file refs (cert paths materialized to temp files) → inject meta/pool defaults → match on `client` (wire driver) → refine on `meta.dbtype` (managed-service flavor) → construct. Vendor subclasses override only what their platform breaks: Tidb/Vitess extend MysqlClient, Yugabyte extends PgClient. The sync named class vs async default export split exists because SSL cert files need async fs work; everything internal that wants SSL support must import the DEFAULT export.

**Invariant:** (1) Dispatch keys on `client` FIRST and `meta.dbtype` SECOND — porters who flatten this to one level lose TiDB/Vitess/Yugabyte routing. (2) The factory never opens connections itself; when called through NcConnectionMgrv2 the SAME knex pool backs both the ORM layer and the introspection client (`connectionConfig.knex` short-circuit) — creating a second pool here leaks connections per source. (3) `pool` defaults `{min:0,max:5}` are injected at THIS layer, not in each constructor. (4) Unknown combos throw `notImplemented` naming meta.dbtype — never silently fall back to a parent client.

**Probe:** no upstream unit test imports SqlClientFactory (grep of all 109 src/**/*.spec.ts = zero hits) → deterministic source probes: `sed -n '15,30p' packages/nocodb/src/db/sql-client/lib/SqlClientFactory.ts` shows the exact ladder; `grep -c "knex" packages/nocodb/src/db/sql-client/lib/KnexClient.ts` ≥ 6 with the :153 short-circuit present.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "SqlClientFactory create TidbClient VitessClient YugabyteClient", limit: 10 });
```

## Verdict
Adopt the two-level dispatch (wire protocol → dbtype variant) plus the async SSL pre-resolve wrapper and the knex-handle reuse contract; adapt vendor-variant subclass names to host; omit mssql/oracle branches (not wired into this factory at pin).
