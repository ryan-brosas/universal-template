<!-- capsule-v2 -->
# Meta-table upsert translation — how does REST PATCH/PUT on columns/tables compile down to user actions over hidden metatables?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you turn name-addressed schema edits (by tableId/colId) into rowId-addressed updates on metadata tables, and how does PUT's add/update/remove mix stay atomic?

## findMatchingRowId resolves names→rowIds (404 otherwise); PUT builds UpdateRecord+AddVisibleColumn+BulkRemoveRecord lists and applies them as ONE action bundle
**Path/Symbol:** `app/server/lib/DocApi.ts:PATCH /columns` (:757–778), `PATCH /tables` (:781–796), `PUT /columns` (:816–861), `DELETE /columns/:colId` (:863–873); resolver pattern `activeDoc.docData.getMetaTable("_grist_Tables")`.
**Signature:** PATCH uses `getTableOperations(req, activeDoc, "_grist_Tables_column")` (ops bound to the META table, not :tableId); PUT hand-builds `UserAction[]`.
**Data Shape:** metatables `_grist_Tables` (keyed `tableId`), `_grist_Tables_column` (keyed `parentId`+`colId`; `colRef` links a column record to its data-column identity). PUT query flags: `noupdate`, `noadd`, `replaceall`.

### Decisive source
```ts
const tableRef = tablesTable.findMatchingRowId({ tableId });
if (!tableRef) { throw new ApiError(`Table not found "${tableId}"`, 404); }
// PUT /columns core:
for (const col of body.columns) {
    const id = columnsTable.findMatchingRowId({ parentId: tableRef, colId: col.id });
    if (id) { updateActions.push(["UpdateRecord", "_grist_Tables_column", id, col.fields]);
              updatedColumnsIds.add(id); }
    else    { addActions.push(["AddVisibleColumn", tableId, col.id, col.fields]); }
}
const getRemoveAction = async () => {
    const columns = await activeDoc.getTableCols(docSessionFromRequest(req), tableId);
    const columnsToRemove = columns.map(col => col.fields.colRef)
      .filter(colRef => !updatedColumnsIds.has(colRef));
    return ["BulkRemoveRecord", "_grist_Tables_column", columnsToRemove];
};
const actions = [
    ...(!isAffirmative(req.query.noupdate) ? updateActions : []),
    ...(!isAffirmative(req.query.noadd) ? addActions : []),
    ...(isAffirmative(req.query.replaceall) ? [await getRemoveAction()] : []),   // LAST
];
await handleSandboxError(tableId, [], activeDoc.applyUserActions(docSessionFromRequest(req), actions));
```
**Flow:** PATCH resolves each requested column/table to its meta-rowId up front (missing → 404 with the NAME in the message) then delegates to TableOperationsImpl.update against the meta table. PUT instead classifies each incoming column as update-or-add, optionally computes removals by set-difference on colRef, and submits everything as one applyUserActions bundle — single undo unit, single sandbox round-trip. Removal identity is colRef, NOT colId (renames survive replaceall).
**Invariant:** name→rowId resolution must happen server-side against CURRENT metadata (never trust client-supplied rowIds for schema entities). replaceall removals are computed from PRE-action metadata and go LAST in the action array: `getRemoveAction` reads `getTableCols` before anything is applied, so removal = "every existing column whose colRef is not among this request's UPDATES". Freshly added columns survive because their colRefs don't exist yet in the table's column list; keying on colRef rather than colId means renames inside the same request still match for survival.
**Probe:** `test/server/lib/docapi/DocApiColumns.ts` (columns CRUD suite) + `DocApiTables.ts` (PATCH /tables 404 paths). Coverage caveat: the replaceall colRef set-difference edge (rename survival) is source-pinned; suites assert status codes rather than action composition.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "findMatchingRowId _grist_Tables_column BulkRemoveRecord AddVisibleColumn replaceall", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt meta-table translation for schema-editing APIs over a self-describing store. Adapt action names to your engine. Keep the colRef-vs-colId distinction — keying removals on mutable names is the classic porter bug.
