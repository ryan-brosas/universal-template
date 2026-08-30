<!-- capsule-v2 -->
# Delete-context FK sweep — how are outgoing AND incoming link edges cleaned when records are deleted?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What two complementary queries build the cell contexts that unlink a deleted record from every referencing table?

## getContextByDelete / getRelatedLinkFieldRaws / getJoinedForeignKeys
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:getDeleteRecordUpdateContext` (:2003–2022) → `:getContextByDelete` (:1868–1935), `:getRelatedLinkFieldRaws` (:1955–2002), `:getJoinedForeignKeys` (:654–676), `:getDirectForeignKeys` (:1936–1954), `:parseFkRecordItemToDelete` (:1805–1867).
**Signature:** `getDeleteRecordUpdateContext(tableId: string, records: IRecord[]): Promise<{[tableId]: ICellContext[]}>`.
**Data Shape:** Contexts keyed by OWNING table of the link field (may differ from deleted table); each `{fieldId, recordId, oldValue, newValue: null}`.

### Decisive source
```ts
// Process link fields belonging to the current table itself
// Query junction tables directly to handle cases where record.fields has null values
// but junction table still has data (data inconsistency)
for (const linkField of currentTableLinkFields) {
```
(Discovery is dual-channel — reference graph PLUS raw options scan:)
```ts
const foreignTableSql = this.dbProvider.optionsQuery(FieldType.Link, 'foreignTableId', tableId);
...
relatedFieldsByForeignTable
  .filter((field) => !knownFieldIds.has(field.id) && !field.deletedTime && !this.isErroredLinkField(field))
  .forEach((field) => merged.set(field.id, field));
```
(Self-side sweep uses a SELF-JOIN subquery, not the simple IN:)
```ts
const query = this.knex(fkHostTableName)
  .select({ id: selfKeyName, foreignId: foreignKeyName })
  .whereIn(selfKeyName, function () {
    this.select(selfKeyName).from(fkHostTableName)
      .whereIn(foreignKeyName, linkRecordIds).whereNotNull(selfKeyName);
  })
  .whereNotNull(foreignKeyName)
  .toQuery();
```

**Flow:** Incoming edges: for each OTHER-table link field pointing here, `getJoinedForeignKeys` finds junction rows whose FOREIGN side references the dying records → `parseFkRecordItemToDelete` computes per-record removals (scalar vs array by relationship; no-op rows filtered). Outgoing/self edges: fields OWNED by the dying table are swept with `getDirectForeignKeys` so orphaned junction data (cell JSON already null) still yields cleanup contexts. Field discovery merges reference-graph hits with an options-JSON scan because legacy bases may lack reference rows.
**Invariant:** The delete sweep must be resilient to PRE-EXISTING inconsistency (junction rows without cell values) and to MISSING reference-graph coverage (options-scan fallback) — trusting either single channel under-cleans and leaks dangling links.
**Probe:** `grep -cF 'getDirectForeignKeys' apps/nestjs-backend/src/features/calculation/link.service.ts` → ≥2; `grep -cF "optionsQuery(FieldType.Link, 'foreignTableId', tableId)" <same>` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getContextByDelete getRelatedLinkFieldRaws getDeleteRecordUpdateContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-channel field discovery + direct-junction self-sweep on deletes; adapt to your metadata store; omit teable's errored-field filtering if you have no broken-field state.
