<!-- capsule-v2 -->
# Create-visitor builder fusion — how do rules feed BOTH a CREATE TABLE builder and post-create ALTER statements without duplicating column definitions?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** When creating a table with all its fields, which rules become inline columns and which stay as follow-up statements?

## PostgresTableSchemaFieldCreateVisitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/PostgresTableSchemaFieldCreateVisitor.ts` — dual constructors (:97–138), `addCreateTableColumnFromRules` (:196–280), `apply()` tableLocations merge (:151–178).
**Signature:** static `forTableCreation({builderRef: {builder}, ...})` mutates a shared CreateTableBuilder via ref object; static `forSchemaUpdate({...})` returns ALTER statements; private ctor enforces the split.
**Data Shape:** skip sets by rule-id prefix: inline-handled = `column:`, `link_value_column:`, `generated_column:` (+suppressed `generated_meta:`), `fk_column:`, `order_column:`; everything else (indexes, uniques, junctions, FK constraints, references, meta) remains for resolver.upAll.

### Decisive source
```ts
// generated column ⇒ typed inline add; plain column ⇒ resolveColumnType; link value ⇒ jsonb
if (generatedColumnRule) {
  this.builderRef.builder = this.builderRef.builder.addColumn(
    columnName, generatedColumnRule.createTableColumnType());
  skipRuleIds.add(generatedColumnRuleId);
} else if (rules.some((rule) => rule.id === columnRuleId)) {
  const dataType = yield* resolveColumnType(field);
  this.builderRef.builder = this.builderRef.builder.addColumn(columnName, dataType);
  skipRuleIds.add(columnRuleId); skipRuleIds.add(`generated_meta:${fieldId}`);
}
// helper columns (fk/order) dedupe across fields sharing one host column:
if (!this.createTableHelperColumnNames.has(fkColumn.columnName)) {
  this.builderRef.builder = this.builderRef.builder.addColumn(fkColumn.columnName, fkColumn.dataType);
  this.createTableHelperColumnNames.add(fkColumn.columnName);
}
```

**Flow:** apply(table) first MERGES the table's own location into tableLocationsById so link rules can resolve sibling tables during batch creation → per field create rules → in creation mode, inline eligible columns into the builder and strip their rule ids; remaining rules go through schemaRuleResolver.upAll as usual. Helper-column dedup set prevents symmetric-link twins from adding one `__fk_*` column twice.
**Invariant:** the builderRef is an OBJECT (`{builder}`) because visitor methods reassign it — passing the builder directly would mutate nothing; a field whose column went inline must NOT also emit its own ADD COLUMN statement (skip set), or CREATE TABLE and ALTER would fight.
**Probe:** graph probe search_graph 'addCreateTableColumnFromRules buildTableLocationsById'; behavior exercised by integration CreateTableHandler.db.spec.ts; unit coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableSchemaFieldCreateVisitor forTableCreation addCreateTableColumnFromRules ICreateTableBuilderRef", limit: 10 });
```

## Verdict
Adopt rule-to-inline-column classification with skip-set bookkeeping, ref-object builder mutation, cross-field helper-column dedup, and self-location merging; adapt to your DDL builder API; omit if you never batch-create multi-table schemas.
