<!-- capsule-v2 -->
# Field persistence row builder — how does teable serialize v2 domain fields into v1-compatible `field` rows (options JSON shapes, lookup flattening, conditionalLookup type masquerade)?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What exact JSON goes into `options` vs `lookup_options` vs `meta` per field type, and which DTO-vs-domain fallback wins when metadata is incomplete?

## three-column split + v1-compat flattening + DTO-first/domain-fallback resolution
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/TableFieldPersistenceBuilder.ts` — `buildDbFieldMeta` (117–131), `buildRowForField` (165–185), `buildRowValue` (286–349), `serializeFieldOptions` (351–382), `serializeLookupOptions` (384–427), `extractLookupInnerOptions` (554–584), `resolvePersistedFieldType` (635–639); tests `TableFieldPersistenceBuilder.spec.ts` :30+, `TableMetaUpdateVisitor.spec.ts` 'preserves lookup inner options…' :259.
**Signature:** `buildRowForField(field: Field): Result<TableFieldRow, DomainError>`; `buildDbFieldMeta(): Result<ReadonlyArray<ITableDbFieldMeta>, DomainError>`; `TableFieldRow` = 29-column literal shape (id/name/options/meta/ai_config/type/cell_value_type/is_multiple_cell_value/db_field_type/db_field_name/not_null/unique/is_primary/is_computed/is_lookup/is_conditional_lookup/has_error/lookup_linked_field_id/lookup_options/table_id/order/version/created_time/last_modified_time/deleted_time/created_by/last_modified_by/description).

### Decisive source
```ts
// options column:
if (field.type === 'conditionalLookup') return JSON.stringify(innerOptions);          // INNER type's options only
if (field.type === 'conditionalRollup') return JSON.stringify({ ...resolvedFieldOptions,
  foreignTableId: config.foreignTableId, lookupFieldId: config.lookupFieldId,
  filter: condition?.filter ?? null, sort: condition?.sort, limit: condition?.limit }); // FLATTENED config (v1 format)
return JSON.stringify(resolvedFieldOptions);
// lookup_options column (serializeLookupOptions): conditionalLookup → {foreignTableId,lookupFieldId,filter,sort,limit};
// plain lookup → {...normalizeLookupLinkedOptions(linkOptions), ...lookupDefinition, linkFieldId}; rollup → link-options merge too
// resolvePersistedFieldType: conditionalLookup persists its innerType (default 'singleLineText') as row.type
// extractLookupInnerOptions: regular lookup-of-formula strips foreign expression via toRegularLookupFormulaOptions (T6332)
```

**Flow:** resolve DTO-first (`dto.fields.find(id)`) falling back to live domain getters (`lookupOptionsDto()`, `configDto()`, `innerOptionsPatch()` merged over inner options) → mint/adopt dbFieldName → assemble row: booleans persist `null` (not false) when absent — v1 convention where null means "no opinion"; `is_primary: true` only for the table's primary field else null; `version: 1`; order is index+1 from table field sequence.
**Invariant:** the `options`/`lookup_options` SPLIT is load-bearing: v1 readers reconstruct lookups from `lookup_options` and the inner field's own `options`; putting condition data in the wrong column breaks v1 interop silently. Regular lookup-of-formula must NOT persist the foreign formula expression (regression T6332) but conditional-lookup formulas keep theirs because filtered evaluation needs it. `normalizeLookupLinkedOptions` drops default `isOneWay:false` and `symmetricFieldId` to keep rows byte-comparable with v1-written rows.
**Probe:** `TableMetaUpdateVisitor.spec.ts` 'preserves lookup inner options in add-field statements when mapper DTO metadata is incomplete' (:259) exercises the domain-fallback path end-to-end.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableFieldPersistenceBuilder buildRowValue serializeLookupOptions extractLookupInnerOptions", limit: 10 });
```

## Verdict
Adopt the whole builder as the canonical field-row serializer; the v1-flattening shapes are wire-format contracts — copy them exactly. Adapt only the DTO interface names. Omit nothing: every branch exists because a v1 consumer reads that column.
