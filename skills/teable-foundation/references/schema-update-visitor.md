<!-- capsule-v2 -->
# Spec-driven schema update visitor — how do 60+ table specs funnel into DDL, search-index maintenance, and record-level side effects in one pass?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the update visitor keep statement generation, GIN trigram index lifecycle, and record-update capture consistent across add/remove/convert/options-change specs?

## TableSchemaUpdateVisitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/TableSchemaUpdateVisitor.ts` — class (:140), `getSearchIndexName` (:154–171, 63-char PG limit with table-name truncation ladder), `dropManagedSearchVectorColumnsStatement` (:203–239), `createSearchIndexStatement` (:277–343), `visitTableUpdateFieldType` (:859–926), select-options renames/removes (:1356–1515); composition root wiring in `repositories/PostgresTableSchemaRepository.ts` update() (:703–846).
**Signature:** extends `AbstractSpecFilterVisitor<ReadonlyArray<TableSchemaStatementBuilder>>` — where `and`/`or` are ARRAY CONCAT and `not` is identity (statement lists have no boolean algebra; addCond just accumulates).
**Data Shape:** params carry a `recordUpdateCollector` sink; option-removal statements RETURN `{recordId, oldVersion, newVersion, oldValue, newValue}` rows that flow into domain events as `RecordsBatchUpdated`.

### Decisive source
```ts
// type-conversion statement ORDER is load-bearing:
const statements = [
  visitor.markSearchVectorConfigRebuildPendingStatement('source_field_type_changed'),
  visitor.dropManagedSearchVectorColumnsStatement(), // generated tsv columns BLOCK ALTER TYPE
  dropSearchIdx,                                     // drop old trgm index first
  ...conversionStatements,
  ...referenceStatements,                            // meta-plane reference rewrites
  ...(createSearchIdx ? [createSearchIdx] : []),     // recreate AFTER conversion
];
```

**Flow:** add-field ⇒ rebuild-pending marker + create-visitor rules + conditional search index; remove-field ⇒ marker + managed-column dropper + delete-visitor rules; options rename ⇒ per-option scalar/jsonb_agg UPDATEs; removal ⇒ NULL-ing (single) or jsonb filter (multi) UPDATE with `__version` bump + RETURNING-fed collector; constraint changes emit SET/DROP NOT NULL + ADD CONSTRAINT UNIQUE vs DROP CONSTRAINT+DROP INDEX pairs.
**Invariant:** search indexes are OPT-IN via a DO-block guard (`IF EXISTS idx_trgm% on table`) so tables without search never grow indexes; boolean/multi-date cell types never get indexes; longText expressions newline-normalize before trigram indexing; every spec path marks the search-vector config `rebuild_pending` with a staleReason.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/TableSchemaUpdateVisitor.pglite.spec.ts:877 'should replace oneOne unique FK constraint when converting to manyOne'`; unit spec TableSchemaUpdateVisitor.spec.ts documents intended SQL via it.todo catalog (:32–260).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableSchemaUpdateVisitor getSearchIndexName markSearchVectorConfigRebuildPending regenerateFieldReferences", limit: 10 });
```

## Verdict
Adopt the concat-algebra filter visitor, the ordered conversion choreography (marker→drop-generated→drop-index→convert→references→reindex), opt-in guarded index creation, and version-bumping RETURNING collectors feeding domain events; adapt index naming/truncation rules to host conventions; omit the specific trgm operator class if host uses another FTS backend.
