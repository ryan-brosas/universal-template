<!-- capsule-v2 -->
# Query builder mode manager — when do reads use computed laterals vs stored columns, and who prepares what?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is the read path switched between computed and stored modes, and which flags pin the computed builder's output shape?

## Manager-created, prepare()d builders behind one interface
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/TableRecordQueryBuilderManager.ts` — whole file (120L); contract `ITableRecordQueryBuilder.ts` (`DynamicDB = Record<string, Record<string, unknown>>`, `SystemColumn` incl. `` `__row_${string}` ``, `prepare(deps)` before `build()`).
**Signature:** `createBuilder(context, table, { mode?: 'computed'|'stored', sourceTableName? }): Result<ITableRecordQueryBuilder, DomainError>`; default mode is `'stored'`.
**Data Shape:** computed instantiation pins `{ typeValidationStrategy (DI), preferStoredLastModifiedFormula: true, forceLookupArrayOutput: true }`.

### Decisive source
```ts
const builder = mode === 'stored'
  ? new StoredTableRecordQueryBuilder(db, { sourceTableName }).from(table)
  : new ComputedTableRecordQueryBuilder(db, {
      typeValidationStrategy: this.typeValidationStrategy,
      preferStoredLastModifiedFormula: true,
      forceLookupArrayOutput: true,   // lookups ALWAYS come back arrays in computed reads
    }).from(table);
// prepare({ context, tableRepository }) runs BEFORE build(): computed mode loads
// foreign tables there; stored mode is a no-op.
```

**Flow:** create → tracer spans nest creation→prepare so pg queries become children → caller chains select/limit/orderBy/where then `build()` returns a Kysely SelectQueryBuilder over DynamicDB.

**Invariants:**
1. **DynamicDB everywhere**: the package mandates one dynamic schema generic for ALL Kysely usage (doc-comment DO/DON'T) instead of ad-hoc record types.
2. Computed-mode lookup outputs are forced array-shaped at the builder level — consumers must not re-normalize.
3. `sourceTableName` lets a CTE-backed permission view substitute the physical table without touching field resolution.
4. Ordering keys are `FieldId | SystemColumn` where system includes per-view ``__row_${viewId}`` columns.

**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.spec.ts` + `.formula/.systemFields/.userFields` visitor specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableRecordQueryBuilderManager forceLookupArrayOutput", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt prepare-then-build with mode objects. Adapt DI of type-validation strategy to your container. Omit formula-SQL internals (separate package surface).
