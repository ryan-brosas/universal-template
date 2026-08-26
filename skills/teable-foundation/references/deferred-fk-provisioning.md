<!-- capsule-v2 -->
# Deferred FK creation for batch table provisioning — why are foreign keys withheld during multi-table CREATE and applied in a second pass?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does creating many tables in one transaction avoid forward-reference failures on cross-table FKs?

## ensureDeferredForeignKeys (PostgresTableSchemaRepository :234–301)
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/repositories/PostgresTableSchemaRepository.ts` — `ensureDeferredForeignKeys` (:234–301); pairs with create-path statement generation that omits `fk:`/`junction_fk:` rules until tables exist.
**Signature:** `ensureDeferredForeignKeys(context, tables: ReadonlyArray<Table>, options?: {optimizeForEmptyTables?}): Promise<Result<void>>`.
**Data Shape:** rule-id prefixes act as the deferral contract: exactly `'fk:'` and `'junction_fk:'` rules are second-pass; everything else (columns, junction tables, indexes, uniques, meta rows) is first-pass.

### Decisive source
```ts
for (const field of table.getFields()) {
  const rules = yield* createFieldSchemaRules(field, {schema, tableName, tableId});
  const deferredFkRules = rules.filter(
    (rule) => rule.id.startsWith('fk:') || rule.id.startsWith('junction_fk:'));
  if (deferredFkRules.length === 0) continue;
  for (const rule of deferredFkRules) {
    const statements = yield* rule.up(ctx);   // ctx carries optimizeForEmptyTables
    await executeTableSchemaStatements(db, statements, {...,
      attributes: { ..., 'teable.schema.statement.source': 'deferred_foreign_key' }});
  }
}
```

**Flow:** batch create: per table build full rule sets but execute only non-FK rules (columns/junctions/indexes/meta) → after ALL tables' physical shells exist, iterate every field again executing ONLY the FK rules — by then every referenced physical table is guaranteed present, so the DO-block guards rarely fire; tracer attribute tags these statements distinctly for observability.
**Invariant:** deferral is keyed on RULE-ID PREFIXES, not types — adding a new FK-emitting rule requires registering its prefix here or it will run too early; the second pass re-derives contexts (fresh introspector) so nothing depends on stale first-pass state.
**Probe:** graph probe trace inbound on ensureDeferredForeignKeys from insertMany path; source pin PostgresTableSchemaRepository.ts :273–296. No dedicated spec — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ensureDeferredForeignKeys deferredFkRules optimizeForEmptyTables insertMany", limit: 10 });
```

## Verdict
Adopt two-pass provisioning (structure first, cross-table constraints second) with prefix-keyed deferral and observability tagging; adapt to host DDL runner shape; omit if your schema tooling already topo-orders tables.
