<!-- capsule-v2 -->
# Migration log storage — what must a migration bookkeeping table guarantee?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** What is the smallest storage contract a migration runner needs, and when may it create its own table?

## Lazy table creation inside executed(); name-keyed insert/delete log
**Path/Symbol:** `packages/core/database/src/migrations/storage.ts` : `createStorage` (8–47).
**Signature:** `createStorage({ db, tableName }) → { async logMigration({name}), async unlogMigration({name}), async executed(): Promise<string[]> }`.
**Data Shape:** table `(id increments, name string, time datetime)`; `executed()` returns names ordered by time.

### Decisive source
```ts
const hasMigrationTable = () => db.getSchemaConnection().hasTable(tableName);

async executed() {
  if (!(await hasMigrationTable())) {
    await createMigrationTable();
    return [];                                  // fresh DB: nothing executed, table now exists
  }
  const logs = await db.getConnection(tableName).select().from(tableName).orderBy('time');
  return logs.map((log: { name: string }) => log.name);
},

async logMigration({ name }) {
  await db.getConnection().insert({ name, time: new Date() }).into(tableName);
},
async unlogMigration({ name }) {
  await db.getConnection(tableName).del().where({ name });
},
```

**Flow:** first read of an empty database creates the log table and reports zero executed migrations; every successful up inserts `(name, now)`; down deletes by name. The same factory instantiates **separate tables per provider** — `strapi_migrations` for app migrations, `strapi_migrations_internal` for framework migrations.
**Invariant:** `executed()` must be safe before any migration ever ran (lazy create), and its returned list is the *only* source of truth for pending computation. Table creation here bypasses the schema-diff engine on purpose: the log tables are infrastructure, not content schema.
**Probe:** `src/migrations/__tests__/resolver.test.ts:110+` ('creates the table and tracks executed migrations' integration) and `src/migrations/__tests__/internal-upgrade-simulation.test.ts` (whole file) — pre-logged names suppress every `up()` spy; partially-logged state runs exactly the pending suffix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "migration storage lock shouldRun execute", limit: 30, fields: ["lines", "signature"] });
// returned migrations.storage.createStorage @ storage.ts 8-47 with logMigration/unlogMigration/executed
```

## Verdict
Adopt the three-method storage interface and lazy-create-in-executed semantics. Adapt the table schema (add checksum/batch columns if your runner needs them). Omit Strapi's specific table names unless you need dual-stream parity with the provider-composition capsule.
