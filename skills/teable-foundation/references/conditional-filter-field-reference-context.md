<!-- capsule-v2 -->
# conditional-filter-field-reference-context — How do conditional filters resolve field references that point at the HOST table while compiling against the foreign table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What do `fieldReferenceSelectionMap` / `fieldReferenceFieldMap` supply to filterQuery?

## buildFieldReferenceContext maps host ids→mainAlias refs, foreign ids→foreignAlias refs; same-table scopes swap
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:buildFieldReferenceContext` (:838-841 wrapper region :810-841) + consumption at :1476-1490 (residual) and :1569-1583 (full filter).
**Signature:** `buildFieldReferenceContext(table, foreignTable, mainAlias, foreignAlias): { fieldReferenceSelectionMap, fieldReferenceFieldMap }`.
**Data Shape:** same-table scope: every field maps to the FOREIGN alias (host record's fields read as foreign-row fields); distinct tables: host ids→mainAlias, foreign ids→foreignAlias with no overwrite.

### Decisive source
```ts
if (table.id === foreignTable.id) {
  for (const field of table.fields.ordered) {
    fieldReferenceSelectionMap.set(field.id, `"${foreignAlias}"."${field.dbFieldName}"`);
  }
  return ...;
}
for (const field of table.fields.ordered)
  fieldReferenceSelectionMap.set(field.id, `"${mainAlias}"."${field.dbFieldName}"`);
for (const field of foreignTable.fields.ordered)
  if (!fieldReferenceSelectionMap.has(field.id))
    fieldReferenceSelectionMap.set(field.id, `"${foreignAlias}"."${field.dbFieldName}"`);
```

**Flow:** conditional rollup/lookup filters may reference BOTH sides (`{HostField}` vs plain fieldId) → filterQuery receives the dual map so `{...}` tokens compile to host-qualified SQL and bare ids to foreign-qualified → residual equality plan uses the same context for its remaining predicates.
**Invariant:** first-wins insertion order means a host field id colliding with a foreign id resolves to the HOST — deliberate, because `{curly}` syntax is the only way users reference the host side. Same-table conditionals MUST alias everything through the foreign scope or the predicate would compare the row against itself.
**Probe:** static byte-exact: `grep -n 'fieldReferenceSelectionMap' field-cte-visitor.ts | head -4`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildFieldReferenceContext","limit":3,"detail":"ids"}'
```

## Verdict
Adopt dual-map resolution with first-wins host priority. Adapt token grammar. Omit nothing.
