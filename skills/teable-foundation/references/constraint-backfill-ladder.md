<!-- capsule-v2 -->
# Constraint backfill ladder — in what order must column, default-backfill, and NOT NULL rules be chained so existing rows never block a required constraint?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does adding a NOT NULL constraint to a populated column stay repairable, and when is it declared un-repairable?

## ColumnExists → DefaultValueBackfill → NotNull chain
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/ColumnExistsRule.ts` — `createRulesFromField` (:86–101), `shouldHaveNotNull` (:44–50); `field/DefaultValueBackfillRule.ts` whole (144L); `field/NotNullConstraintRule.ts` — isValid null-count branch (:46–104), repair hint (:106–140).
**Signature:** `createRulesFromField(field): ISchemaRule[]` = `[column]` + (notNull? `[defaultBackfill?, notNull]`) + (unique? `[uniqueConstraint]`); backfill rule `id='default_backfill:fldX'`, `required=false`, deps `[column.id]`; NotNull rule deps `[backfillRule.id]` — the constraint depends on the BACKFILL, not directly on the column.
**Data Shape:** default literal resolved through three visitors: `FieldDefaultValueVisitor` (domain default) → `FieldInsertValueVisitor` (insert-shape value with sentinel recordId `'__schema_default_backfill__'`) → `FieldSqlLiteralVisitor` (escaped SQL literal); `undefined` at any hop ⇒ no backfill statements.

### Decisive source
```ts
// DefaultValueBackfillRule.up — fill only NULLs, only when a usable default exists
const statement = sql.raw(
  `UPDATE ${tableRef} SET ${columnRef} = ${defaultLiteral} WHERE ${columnRef} IS NULL`);
// down() returns ok([]) — data backfill has no inverse

// NotNullConstraintRule.isValid — distinguish "constraint missing" from "data blocks us"
if (columnInfo.isNullable) {
  const nullCount = await self.countNullValues(ctx, columnName);
  if (nullCount > 0) return ok({ valid:false, missing:[`${nullCount} NULL values...`],
    missingItems:[{ code:'not_null_existing_nulls', message:{values:{count:nullCount}}, ...}]});
}
```

**Flow:** column exists → if field requires NOT NULL AND type permits it (`checkFieldNotNullValidationEnabled(type,{isComputed})`) → optional backfill fills NULL rows from the field default → THEN the NOT NULL rule can pass; if NULLs remain that have no default, validation reports code `not_null_existing_nulls` and the repair hint returns `{available:false}` with user guidance ('fill or relax in Base design first') — auto-repair refuses rather than destroying data.
**Invariant:** constraints are separate REQUIRED-flagged rules so the checker can warn (optional) or error (required) independently; backfill sits BETWEEN column and constraint in dependency order — porters who wire NotNull→Column directly lose the repair path.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/SchemaRules.pglite.spec.ts:1103 'should not advertise automatic repair when existing NULL values block NOT NULL'`; backfill covered via FkColumnRule pglite :1151 'backfill FK values from the persisted link JSON column'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "DefaultValueBackfillRule createRulesFromField not_null_existing_nulls FieldSqlLiteralVisitor", limit: 10 });
```

## Verdict
Adopt the column→backfill→constraint chain with the typed blocking-data failure code and refuse-to-guess hint; adapt visitor trio to your value-conversion layer; omit teable's computed-field enablement matrix specifics.
