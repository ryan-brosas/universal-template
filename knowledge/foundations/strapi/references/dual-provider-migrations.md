<!-- capsule-v2 -->
# Dual-provider migration composition — how do framework migrations coexist with app migrations?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** A framework ships its own data migrations while user apps ship theirs — how do you run both without interference and who goes first?

## Two providers, two log tables, fixed order, per-migration transactions
**Path/Symbol:** `packages/core/database/src/migrations/index.ts` : `createMigrationsProvider` (whole module, 41 lines); `internal.ts` : `createInternalMigrationProvider` (10–44); `users.ts` : `createUserMigrationProvider` (14–46); `common.ts` : `wrapTransaction` (49–51); `resolver.ts` : `migrationResolver` (10–40).
**Signature:** `createMigrationsProvider(db) → { providers: { internal }, shouldRun(), up(), down() }`; each sub-provider exposes `{ register?, shouldRun, up, down }`.
**Data Shape:** user stream = files discovered from `config.settings.migrations.dir`; internal stream = in-memory array seeded with `internalMigrations` plus runtime `register()`.

### Decisive source
```ts
const userProvider = createUserMigrationProvider(db);
const internalProvider = createInternalMigrationProvider(db);
const providers = [userProvider, internalProvider];      // fixed order

async up() {
  for (const provider of providers) {
    if (await provider.shouldRun()) {
      await provider.up();
    }
  }
}

// users.ts — the ONLY provider honoring the opt-out:
async shouldRun() {
  const pendingMigrations = await runner.pending();
  return pendingMigrations.length > 0 && db.config?.settings?.runMigrations === true;
}
// users.ts getMigrations(): discoverMigrationFiles(dir) → resolveMigrationFiles(...) via
//   migrationResolver (.sql → knex.raw(sql), down throws 'Down migration is not supported
//   for sql files'; .js → require(path)); every body wrapped:
// common.ts:
export const wrapTransaction = (db: Database) => (fn: MigrationFn) => () => {
  return db.transaction(({ trx }) => Promise.resolve(fn(trx, db)));
};
```

**Flow:** `shouldRun()` fans out over both providers (Promise.all + `.some`) — this is what the schema-sync gate consults. `up()` runs user stream first, then internal, each migration inside its own transaction via `wrapTransaction`, each logging to its own table (`strapi_migrations` / `strapi_migrations_internal`).
**Invariant:** ordering is structural (user before internal — an internal migration may assume app tables exist), not timestamp-based; the `runMigrations:false` opt-out silences *only* the user stream because framework upgrades must never be skipped by app config. Per-migration transactions mean a failed migration rolls back alone but earlier successes stay committed and logged.
**Probe:** `src/migrations/__tests__/providers.test.ts:334–363` ('runs user migrations before internal migrations' — internal migration asserts the user table exists or throws); `:181–214` (failed user migration stops the stream unlogged); `src/migrations/__tests__/resolver.test.ts:72–85` (.sql up works, down rejects).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "runner pending up wrap migration error", limit: 25, fields: ["lines", "signature"] });
// returned createInternalMigrationProvider @ internal.ts 10-44, createUserMigrationProvider @ users.ts 14-46,
// migrationResolver @ resolver.ts 10-40, wrapTransaction @ common.ts 49-51
```

## Verdict
Adopt dual-stream separation with dedicated log tables and a hard-coded stream order when one stream may depend on the other's side effects. Adapt file discovery (`discoverMigrationFiles` sorted js/sql, no recursion) and the `register()` extension point to your plugin system. Omit Strapi's `[internal migration]:` log prefix transform and its specific 5.0.0 upgrade bodies.
