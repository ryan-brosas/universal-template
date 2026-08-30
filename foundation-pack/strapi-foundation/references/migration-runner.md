<!-- capsule-v2 -->
# Migration runner — how do you guarantee each migration runs exactly once with attributable failures?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** What is the minimal runner loop that makes migrations idempotent across restarts and makes the first failed migration obvious?

## Definition-order pending set, log-after-success, name+direction error wrapping
**Path/Symbol:** `packages/core/database/src/migrations/runner.ts` : `createMigrationRunner` (42–116), `getPendingMigrations` (43–51), `wrapMigrationError` (33–40).
**Signature:** `createMigrationRunner(opts: { getMigrations(): Promise<RunnableMigration[]>, storage: { executed, logMigration, unlogMigration }, logger }) → { pending(), up(), down() }`.
**Data Shape:** `RunnableMigration = { name, path?, up(), down()? }`; storage keyed by migration `name` string.

### Decisive source
```ts
const getPendingMigrations = async () => {
  const [migrations, executedNames] = await Promise.all([
    opts.getMigrations(),
    opts.storage.executed(),
  ]);
  const executedSet = new Set(executedNames);
  return migrations.filter((migration) => !executedSet.has(migration.name));
};

async up() {
  const toBeApplied = await getPendingMigrations();
  for (const migration of toBeApplied) {
    try {
      await migration.up();
    } catch (error) {
      throw wrapMigrationError(migration.name, 'up', error); // 'Migration <name> (<dir>) failed: Original error: ...'
    }
    await opts.storage.logMigration({ name: migration.name });  // AFTER success
    logEvent(opts.logger, 'migrated', migration.name, { durationSeconds });
  }
}

async down() {
  const executedReversed = (await getExecutedMigrations()).slice().reverse();
  const toBeReverted = executedReversed.slice(0, 1);            // exactly one step
  for (const migration of toBeReverted) {
    try { await migration.down(); }
    catch (error) { throw wrapMigrationError(migration.name, 'down', error); }
    await opts.storage.unlogMigration({ name: migration.name });
  }
}
```

**Flow:** recompute pending fresh on every call (definition order minus executed name-set) → run sequentially → wrap failures with name+direction+`cause` → log only after success → stop at first failure. Down is deliberately one-step and operates in reverse execution order.
**Invariant:** a migration whose `up()` threw must never be logged — otherwise a restart would skip it while its effects are missing. The log-write placement *after* `migration.up()` is the entire durability contract; ordering comes from the provider's definition order, never from the log table's time column.
**Probe:** `src/migrations/__tests__/runner.test.ts` (whole file): sequential run + nth-call log order; failure wraps with `'Migration 002-second.js (up) failed'`, later migrations untouched, only earlier ones logged; idempotent second `up()`; down reverts last-executed and skips `unlogMigration` when nothing ran.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "runner pending up wrap migration error", limit: 25, fields: ["lines", "signature"] });
// returned runner.pending @ runner.ts 64-67, createMigrationRunner @ 42-116, up @ 69-90, down @ 92-114
```

## Verdict
Adopt the whole runner shape verbatim — it is storage-agnostic and dialect-free. Adapt logging transport and whether down exists at all (Strapi's internal provider never uses multi-step rollback). Omit nothing structural; this is the most directly portable seam in the plane. Coverage: all cited paths `no_recorded_issue`.
