<!-- capsule-v2 -->
# Select-column collection — how does teable build the record SELECT list so field order and duplicate db names stay correct?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A porter must reproduce column ordering, duplicate detection, and dynamic-ref expansion for record queries.

## ordered accumulation + conflict-on-duplicate + record-id-first expansion
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/visitors/TableRecordSelectColumnsVisitor.ts` — `apply` (44–53), `selectColumns` (59–67), `addFieldColumn` (158–171), lookup override comment (145–148); tests `TableRecordSelectColumnsVisitor.spec.ts` 'collects columns in order…' (:98), 'returns a conflict error for duplicate database field names' (:125), 'propagates invalid dbFieldName errors' (:140).
**Signature:** `apply(table): Result<ReadonlyArray<{fieldId, dbFieldName}>>`; `selectColumns(dynamic, recordIdColumn): ReadonlyArray<DynamicReferenceBuilder<string>>`.

### Decisive source
```ts
private addFieldColumn(field: Field): Result<FieldColumn, DomainError> {
  const dbFieldName = yield* field.dbFieldName();
  const column = yield* dbFieldName.value();      // invalid name → error propagates
  if (this.seen.has(column)) return err(domainError.conflict({ message: 'Duplicate DbFieldName' }));
  this.seen.add(column);
  ...
}
// selectColumns puts __id FIRST then every field column in table order:
return [dynamic.ref(recordIdColumn), ...this.columns.map((c) => dynamic.ref(c.dbFieldName))];
```

**Flow:** iterate `table.getFields()` in domain order → per field resolve its dbFieldName through the Result chain (missing/invalid names fail the whole application) → first occurrence wins, duplicates CONFLICT → expansion always leads with the record-id column so row identity survives any later reordering.
**Invariant:** duplicate db_field_names are a CORRUPTION signal (naming minting should have prevented them) and fail loudly as `conflict` — silently deduplicating would drop data columns. Lookup fields get their OWN column (no inner-field delegation) because lookup values materialize into their own storage; delegating to the inner field would select the wrong physical column.
**Probe:** spec :98 pins order + ref expansion; :125 asserts the conflict error path.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableRecordSelectColumnsVisitor addFieldColumn selectColumns", limit: 8 });
```

## Verdict
Adopt ordered accumulation with fail-loud duplicate detection; adapt the Kysely DynamicReferenceBuilder to host query builder. Small but load-bearing for every record read.
