<!-- capsule-v2 -->
# LinkMutationRouting — how a link-field SET compiles to junction/FK SQL per relationship

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** For each link relationship kind, what SQL does a link write emit, and what is the symmetric/foreign-table trap a porter must not get wrong?

## Link field mutation routing
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/CellValueMutateVisitor.ts` (`visitSetLinkValue`, 563-784; `visitSetLinkValueByTitle`, 801-895).
**Signature:** `visitSetLinkValue(spec: SetLinkValueSpec): Result<void, DomainError>` — mutates `setClauses`/`additionalStatements`; `visitSetLinkValueByTitle` returns an error (titles must be pre-resolved to IDs).
**Data Shape:** `rawValue` normalized by `normalizeStoredLinkItems` (filters to `{id:string,title?}` objects). `storedValue` = multiple ? linkItems : `linkItems[0] ?? (rawValue==null?null:rawValue)`; stored as JSON string in the JSONB column.

### Decisive source
```ts
const relationship = linkField.relationship().toString();
if (relationship === 'manyMany' || (relationship === 'oneMany' && linkField.isOneWay())) {
  // junction: DELETE all rows for selfKey=recordId, then INSERT (selfKey, foreignKey[, order=index+1])
} else if (relationship === 'manyOne' || relationship === 'oneOne') {
  const foreignKeyName = yield* linkField.foreignKeyNameString();
  if (foreignKeyName === RECORD_ID_COLUMN) {
    // SYMMETRIC: FK lives on the OPPOSITE table — UPDATE foreignTable SET selfKey=recordId
    //   [selfKey_order=...] FROM (VALUES (id, recordId, order)) WHERE t.__id = v.id
  } else {
    this.setClauses[foreignKeyName] = linkItems[0]?.id ?? null; // FK on main table
  }
} else if (relationship === 'oneMany') { // two-way
  // FK on foreign table: UPDATE foreignTable SET selfKey=null [order=null] WHERE selfKey=recordId (clear),
  //   then UPDATE ... FROM (VALUES ...) to repoint each linked record
}
```

**Flow:** normalize items → if `fillLinkTitles` and missing titles, build a SQL subquery that LEFT JOINs the foreign table to COALESCE titles (see title-fill capsule) → store JSONB column → route by relationship: junction delete+insert, FK-on-main set, or foreign-table clear+repoint. `visitSetLinkValueByTitle` with empty titles clears; non-empty returns `validation.link.title_resolution_required` (async resolution unsupported in the sync visitor).

**Invariant:** The `foreignKeyName === RECORD_ID_COLUMN` guard is load-bearing — symmetric link fields store the FK on the opposite table, so a naive `setClauses[foreignKeyName] = id` would corrupt `__id`. Junction writes use `orderColumnName` = `index+1` when the field `hasOrderColumn()`.

**Probe:** `record/visitors/CellValueMutateVisitor.spec.ts` — `'stores fk values on the main table for many-one links'` (:331), `'builds symmetric clear/update statements when the foreign table owns the fk'` (:446), `'updates foreign-table fk rows for two-way one-many links'` (:545), `'clears junction-backed and foreign-table-backed links when titles are empty'` (:500).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "visitSetLinkValue relationship junction foreignKeyName symmetric", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the relationship-routing ladder and the symmetric-FK guard (the single most likely porting bug). Adapt `RECORD_ID_COLUMN='__id'` naming. Omit the title-fill SQL subquery detail (dedicated capsule). Probes pinned to the real spec suite.
