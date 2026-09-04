<!-- capsule-v2 -->
# Cell-data admission check — how does Grist validate that a user may modify `_grist_Cells` metadata, stepping actions one-by-one through a snapshot and postponing checks until a cell is fully formed?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When a user's bundle touches comment/cell metadata (`_grist_Cells`), how does Grist decide whether each cell mutation is allowed, given that a cell's info may be partially populated across several actions (e.g. on undo)?

## Per-action admission stepping with postponed-until-attached checks + owner exceptions
**Path/Symbol:** `app/server/lib/CellDataAccess.ts` — `applyAndCheckActionsForCells` (:40-184), `isCellDataAction` (:189-191), `CellData.isAttached` (:479-481), `CellData.getCell` (:285-288), `checkChangedIds` (:613-631), `wasToggled` (:636-641). Consumed by `GranularAccess._canApplyCellActions` (`app/server/lib/GranularAccess.ts` :2879-2894).
**Signature:** `applyAndCheckActionsForCells(docData, docActions, directActions: boolean[], userIsOwner, haveRules, userRef, hasAccess: (cell, state) => Promise<boolean>): Promise<void>` — throws `ErrorWithCode("ACL_DENY", "Cannot access cell")` on the first disallowed mutation.
**Data Shape:** operates only on `isCellDataAction` actions (`getTableId(a) === "_grist_Cells" && isDataAction(a)`). A `SingleCellInfo = { id, tableId, colId, rowId, userRef, parentId, content }`; a cell is "attached" when it has `tableId && rowId && colId && userRef`.

### Decisive source
```ts
// Convert bulk to single, step each through the snapshot; postpone until attached + record present.
for (const single of getSingleAction(docAction)) {
  const id = getRowIdsFromDocAction(single)[0];
  if (isAddRecord(single)) {
    docData.receiveAction(single);
    if (haveRules) {
      const cell = cellData.getCell(id);
      if (cell && cellData.isAttached(cell)) {
        const haveRecord = docData.getTable(cell.tableId)?.hasRowId(cell.rowId);
        if (!haveRecord) { postponed.push(id); }
        else if (!await hasAccess(cell, docData)) { fail(); }
      } else { postponed.push(id); }
    }
  } else if (isRemoveRecord(single)) {
    const cell = cellData.getCell(id);
    docData.receiveAction(single);
    if (cell) {
      const record = docData.getTable(cell.tableId)?.getRecord(cell.rowId);
      if (!record || !cell.colId || !(cell.colId in record)) { continue; }
      if (cell.userRef && cell.userRef !== (userRef || "") && !userIsOwner) { fail(); }
    }
    postponed = postponed.filter(i => i !== id);
  } else { // update
    let cell = cellData.getCell(id);
    if (!cell) { return fail(); }
    if (!cell.colId || !cell.tableId || !cell.rowId) { docData.receiveAction(single); continue; }
    if (cellData.isAttached(cell) && haveRules && !await hasAccess(cell, docData)) { fail(); }
    const before = cellData.getCellRecord(id);
    docData.receiveAction(single);
    cell = cellData.getCell(id)!;
    const after = cellData.getCellRecord(id);
    if (cellData.isAttached(cell) && haveRules && !await hasAccess(cell, docData)) { fail(); }
    // anyone may toggle parentId (ON DELETE CASCADE children removed after, not before)
    if (before && after && checkChangedIds(before, after, ["parentId"]) && wasToggled(before, after, "parentId")) { continue; }
    // can't update others' cells unless owner resolving a root comment
    if (cell.userRef && cell.userRef !== (userRef || "")) {
      const isOwnerResolvingRoot = userIsOwner && before && after && after.root &&
        wasToggled(before, after, "resolved") &&
        checkChangedIds(before, after, ["resolved", "timeUpdated"]);
      if (!isOwnerResolvingRoot) { fail(); }
    }
  }
}
```

**Flow:** only direct actions are checked (non-direct actions just step the snapshot). Each direct cell-data action is expanded to singles and stepped through a `CellData` view over the snapshot `docData`. Adds are applied immediately but their access check is postponed until the cell is attached AND its row record exists (on undo, the cell may be created before the row). Removes check ownership (a non-owner can't remove another user's cell) and clear any postponed id. Updates check access before AND after applying (the action may move the cell to a different row/col), allow anyone to toggle `parentId` (the engine's cascade removes children after the parent, so refs are briefly invalid), and forbid updating another user's cell unless the owner is resolving a root comment (only `resolved`+`timeUpdated` changed). After the loop, every still-postponed cell is re-checked: if it never became attached → fail; else if rules exist and access is denied → fail.
**Invariant:** the snapshot `docData` is mutated by every action and is NOT reverted on failure — the caller passes a disposable snapshot (`createSnapshotWithCells`) precisely so a failed admission leaves the live doc untouched. Bulk actions are always expanded to singles before checking. A cell whose info is incomplete is never denied outright — it is postponed and re-checked once fully formed (or failed at the end if it never attached).
**Probe:** `test/server/lib/CommentAccess.ts` — "rejects updates when needed" (:893) and "respects private conversation" (:741) pin the ownership/denial paths; "works across non-trivial bundles" (:797) exercises the postpone-then-check flow.
**Coverage caveat:** the `parentId`-toggle exemption and the owner-resolving-root exception have no isolated unit test (pinned indirectly by the comment suites); the `NEED_ROW_DATA`-style partial-info postpone path is only exercised via undo fixtures.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "applyAndCheckActionsForCells isCellDataAction CellData isAttached", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-action admission stepping over a disposable snapshot, the postpone-until-attached check for partially-formed cells, the ownership guard with the owner-resolving-root exception, and the `parentId`-toggle exemption for cascade timing; adapt the `hasAccess` callback (Grist wires it to the row/column read ladder) and the ownership model; omit the comment-specific `resolved`/`timeUpdated` exception if your cell metadata has no root-comment resolution.
