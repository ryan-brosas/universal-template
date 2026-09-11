<!-- capsule-v2 -->
# Type→rules factory — how does one visitor turn 20 field types into exactly the right rule set, including generated columns and link storage routing?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Where is the authoritative map from field type to physical Postgres schema, and what are the link-relationship branching rules?

## FieldSchemaRulesFactory + column-type resolver
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/FieldSchemaRulesFactory.ts` — `visitLinkField` (:234–355), `createGeneratedColumnAwareRules` (:98–114); column types in `visitors/PostgresTableSchemaFieldColumn.ts` (`columnTypeVisitor`, `resolveFormulaColumnType` :213–222, `resolveLookupColumnType` :230–240).
**Signature:** `createFieldSchemaRules(field, {schema, tableName, tableId, tableLocationsById?, optimizeForEmptyTables?}): Result<ReadonlyArray<ISchemaRule>, DomainError>`.
**Data Shape:** type mapping: text-family⇒`text`; number/rating⇒`double precision`; singleSelect⇒`text`; multipleSelect/attachment/user/createdBy/button⇒`jsonb`; date/createdTime/lastModifiedTime⇒`timestamptz`; autoNumber⇒`integer`; formula/rollup/conditional* derive from cellValueType + isMultipleCellValue (multiple⇒jsonb, number⇒double precision, dateTime⇒timestamptz, boolean⇒boolean, else text).

### Decisive source
```ts
// LINK STORAGE ROUTING — the branch every porter gets wrong:
if (relationship === 'manyMany' || (relationship === 'oneMany' && isOneWay)) {
  // junction table family; withIndexes ONLY for manyMany (one-way oneMany skips them)
  const junctionConfig = {..., withIndexes: relationship === 'manyMany'};
} else {
  // OneOne / regular OneMany: FK COLUMN lives on fkHostTable
  const keyName = relationship === 'oneMany'
    ? yield* field.selfKeyNameString()      // FK points at MY table's rows
    : yield* field.foreignKeyNameString();  // OneOne: FK on foreign side
  const indexRule = relationship === 'oneOne'
    ? UniqueIndexRule.forFkColumn(...)      // one-one ⇒ UNIQUE index
    : IndexRule.forFkColumn(...);           // many-one ⇒ plain index
}

// GENERATED-column duality: persisted-as-generated ⇒ single GeneratedColumnRule;
// otherwise stored column + GeneratedColumnMetaRule that can flip between states
return field.isPersistedAsGeneratedColumn().map((shouldGenerate) =>
  shouldGenerate ? [generatedRule] : this.createStoredGeneratedColumnRules(field, generatedRule));
```

**Flow:** per field: LinkValueColumnRule (JSONB display values) + ReferenceRule(lookup field) always for links → junction or FK branch adds storage rules (+OrderColumnRule+FieldMetaRule when order column present) → two-way links append LinkSymmetricFieldRule; cross-table locations resolve via precomputed `tableLocationsById` (batch creation) else `{schema: baseId||ctx.schema, tableName: foreignTableId}` with the UNRESOLVED case carrying a metaId for deferred resolution.
**Invariant:** rule ORDER inside the returned array is irrelevant (resolver topo-sorts), but dependency WIRING happens in constructors — factory must pass parent rules into children; lookup column typing intentionally mirrors v1 (single-value lookups use scalar PG types).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/LookupColumnType.pglite.spec.ts` (whole-file matrix incl. :272/:654 ranges); factory wiring exercised by SchemaRules.pglite.spec throughout.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FieldSchemaRulesVisitor visitLinkField createStoredGeneratedColumnRules resolveColumnType", limit: 10 });
```

## Verdict
Adopt the type→PG-type table, the three-branch link storage router (junction vs FK-with-index vs FK-with-unique-index), and the generated-vs-stored column duality; adapt field-type names and cellValueType model to host; omit conditional rollup/lookup variants unless host has condition-scoped computed fields.
