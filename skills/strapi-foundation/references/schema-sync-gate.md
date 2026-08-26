<!-- capsule-v2 -->
# Schema sync gate — how do you skip expensive startup DDL without missing real changes?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** At process boot, when can you safely skip re-running schema synchronization, and what must force a full sync anyway?

## Sync gate: migrations first, then hash short-circuit
**Path/Symbol:** `packages/core/database/src/schema/index.ts` : `SchemaProvider.sync` (108–135) and `syncSchema` (74–103).
**Signature:** `async sync(): Promise<SchemaDiff['status']>` / `async syncSchema(): Promise<SchemaDiff['status']>`; `schema` is a lazy getter converting `db.metadata` via `metadataToSchema` once.
**Data Shape:** returns `'CHANGED' | 'UNCHANGED'`; reads persisted `{ id, time, hash, schema }` row; hashes the in-memory schema with sha256.

### Decisive source
```ts
async sync(): Promise<SchemaDiff['status']> {
  if (await db.migrations.shouldRun()) {
    debug('Found migrations to run');
    await db.migrations.up();

    return this.syncSchema();          // migrations ran → force full diff, never trust the hash
  }

  const oldSchema = await this.schemaStorage.read();
  if (!oldSchema) {                    // never persisted → first boot
    return this.syncSchema();
  }

  const { hash: oldHash } = oldSchema;
  const hash = await this.schemaStorage.hashSchema(this.schema);
  if (oldHash !== hash) {
    return this.syncSchema();
  }
  debug('Schema unchanged');
  return 'UNCHANGED';
}
```

**Flow:** pending migrations? → run all providers' up() → full `syncSchema()` regardless of hash. No migrations → read persisted row; absent → sync. Hash mismatch → sync. Hash equal → return `'UNCHANGED'` with **zero** DDL and zero inspector calls.
**Invariant:** the persisted-hash short-circuit is only trustworthy because *every* code path that changes the database outside the diff engine (`migrations.up()`) bypasses it. A porter who runs migrations but still honors the hash will silently skip post-migration drift repair.
**Probe:** `src/schema/__tests__/storage.test.ts` pins the order-insensitive hash half; `src/migrations/__tests__/providers.test.ts:365–376` pins that `shouldRun()` is false after a clean run while both log tables exist — i.e. second boot hits the `'UNCHANGED'` fast path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "schema sync builder synchronize database schema status", limit: 25, fields: ["lines", "signature"] });
// returned strapi.packages.core.database.src.schema.sync @ schema/index.ts 108-135 and syncSchema @ 74-103
```

## Verdict
Adopt the two-gate ordering (migrations-then-hash) and the lazy metadata→schema conversion. Adapt the storage medium for the snapshot row (any durable KV/table works). Omit Strapi's `strapi_core_store_settings` coupling and its TODO list (soft-migrate options). Coverage caveat: `schema/index.ts` is parse-partial at range 11-11 — direct-read verified as a type re-export only; cited symbols unaffected.
