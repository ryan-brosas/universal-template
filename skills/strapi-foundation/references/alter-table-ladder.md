<!-- capsule-v2 -->
# Alter-table operation ladder — in what order must constraint-touching DDL run?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Applying a table diff naively (ALTER COLUMN while a FK still references it) aborts mid-flight on most dialects — what ordering survives?

## Drop foreign keys first, recreate them last
**Path/Symbol:** `packages/core/database/src/schema/builder.ts` : `alterTable` (306–406) inside `updateSchema` (72–134).
**Signature:** `alterTable(schemaBuilder, table: TableDiff['diff'], existingMetadata?: { indexes, foreignKeys })`; `updateSchema(schemaDiff)` wraps everything in one `db.connection.transaction`.
**Data Shape:** consumes the nested diff from the 3-way engine; pre-fetched live `{ indexes, foreignKeys }` per updated table.

### Decisive source
```ts
await db.dialect.startSchemaUpdate();
// ... pre-fetch getIndexes/getForeignKeys per updated table; postgres also
//     pre-fetches column types 'to avoid transaction timeouts' ...
await db.connection.transaction(async (trx) => {
  await this.createTables(schemaDiff.tables.added, trx);
  // forceMigration-gated: dropTableForeignKeys then dropTable for removed
  for (const table of schemaDiff.tables.updated) {
    await helpers.handleSpecialTypeConversions(trx, table, columnTypes[table.name] || {});
    await helpers.alterTable(schemaBuilder, table, { indexes, foreignKeys });
  }
});
await db.dialect.endSchemaUpdate();

// inside alterTable's schemaBuilder.alterTable callback, in order:
// 1. drop removed FKs + drop updated FKs        ('Drop foreign keys first to avoid
//                                                foreign key errors in the following steps')
// 2. mysql only: filter indexes whose name matched a dropped FK
//    ('In MySQL, dropping a foreign key can also implicitly drop an index')
// 3. drop removed + updated indexes
// 4. drop removed columns                       ('after FKs have been removed')
// 5. update columns (.alter()), add new columns
// 6. recreate updated FKs → updated indexes → added FKs → added indexes
```

**Flow:** snapshot live constraint metadata → single transaction → per table: FKs down, indexes down, columns down, columns up, constraints/indexes back up → commit.
**Invariant:** no column drop/alter happens while a foreign key that references it still exists; and index recreation waits until all column mutations are done. The MySQL implicit-index filter prevents the ladder from "recreating" an index that silently vanished with its FK.
**Probe:** no dedicated unit test file for builder ordering (it is knex-bound); behavior boundary is pinned indirectly by the dialect-agnostic diff tests plus the in-source invariant comments — record this as a direct-test caveat when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "schema sync builder synchronize database schema status", limit: 25, fields: ["lines", "signature"] });
// returned builder.updateSchema @ builder.ts 72-134 and alterTable @ 306-406
```

## Verdict
Adopt the ladder order and the one-transaction-per-sync envelope; adopt the pre-fetch of constraint metadata before opening the transaction (postgres lock-timeout hygiene). Adapt `startSchemaUpdate/endSchemaUpdate` hooks and the `forceMigration` gate to your config surface. Omit Strapi's debug tracing. Caveat: ordering itself lacks a direct unit test — treat the source comments as the contract evidence.
