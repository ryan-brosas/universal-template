<!-- capsule-v2 -->
# Conversion dispatch ladder — how does field-type conversion choose between in-place ALTER USING, staged rename-migrate, and full drop+create recreation?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Given oldField→newField, what decides the conversion strategy, and how is data preserved through link/formula conversions?

## generateFieldConversionStatements
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldTypeConversionVisitor.ts` — dispatcher `generateFieldConversionStatements` (:3129–3251), `requiresSchemaRecreation` (:3096–3120), migration builders: `buildFormulaMigrationStatements` (:934–1012) + `buildFormulaMigrationSql` (:1131–1237), `buildScalarToLinkMigrationStatements` (:555–847), `buildLinkToTextMigrationStatements` (:1238–1342), `buildLinkToSelectMigrationStatements` (:1343–1474), `buildLinkToLinkForeignTableMigrationStatements` (:1475–1675), `buildLookupToBasicFieldMigrationStatements` (:1035–1130).
**Signature:** `(params, oldField, newField): Result<ReadonlyArray<TableSchemaStatementBuilder>, DomainError>`; params include `fieldsById` metadata + `tableLocationsById` for preview-time name resolution.
**Data Shape:** strategy ladder (first match wins): ①link→link foreignTable CHANGED ⇒ dedicated remap builder; ②link→text/select ⇒ title-join builders; ③scalar→link ⇒ FK/junction map-by-lookup-value; ④formula→any ⇒ cellValue-typed migration; ⑤lookup/conditionalLookup→basic ⇒ array/scalar extraction; ⑥either side computed/link/autoNumber/system ⇒ drop+create; ⑦else in-place visitor pair.

### Decisive source
```ts
// THE rename→drop→create→migrate→drop-temp spine shared by every staged conversion:
const statements = [
  createCompiledStatementBuilder(params.db, renameSql),      // col → __tmp_<fieldId>
  ...dropStatements,                                          // deleteVisitor rules.down()
  ...createStatements,                                        // createVisitor rules.up()
  ...optionsStatements,                                       // meta-scope select options
  ...(migrateSql ? [builder(migrateSql)] : []),               // typed UPDATE tmp→new col
  createCompiledStatementBuilder(params.db, dropTmpSql),      // DROP COLUMN IF EXISTS __tmp
];
// incompatible formula targets return null migrateSql ⇒ values intentionally NULLed,
// matching v1 semantics — NOT an error.
```

**Flow:** in-place visitors emit ONE `ALTER COLUMN TYPE ... USING <expr>` with regex-guarded casts (`CASE WHEN col ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN col::double precision ELSE NULL END`) or jsonb shape rewrites for user multiplicity flips; staged builders resolve foreign table/column names at EXECUTE time via `fetchLinkMappingMetadata` (meta-db lookups) wrapped as custom statements whose compile() embeds a best-effort PREVIEW sql while execute() rebuilds it from live metadata; DO-blocks no-op when lookup column/table missing.
**Invariant:** the temp-column rename happens BEFORE rule-driven drop so the recovery source survives the drop+create; conversion mode uses `PostgresTableSchemaFieldDeleteVisitor.forConversion` (preserves outbound references) except scalar-to-link and link-to-link which use plain `forSchemaUpdate`.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/FieldTypeConversionVisitor.pglite.spec.ts:477 'should drop junction table and create FK column on foreign table'`, :556/:766 'should preserve link data during migration', :602 'foreign records without junction entries (FK stays NULL)', :945 'junction → FK → junction round-trip'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "generateFieldConversionStatements buildScalarToLinkMigrationStatements alterColumnTypeUsing", limit: 10 });
```

## Verdict
Adopt the ordered strategy ladder, the rename→recreate→migrate→drop-temp spine, regex-guarded lossy casts, and execute-time metadata resolution under a compile-time preview; adapt type names and DO-block templating to host SQL dialect; omit v1-compatibility value semantics if no legacy to mirror.
