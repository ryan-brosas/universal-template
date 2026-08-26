<!-- capsule-v2 -->
# Cell-data censoring patch — how does Grist rebuild `_grist_Cells` metadata for outgoing bundles, censoring cells the user can't read while preserving the engine's own metadata actions?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** On the way out to a client, how does Grist strip `_grist_Cells` metadata actions and re-emit only the cells the user may read, without disturbing the engine's own cell bookkeeping?

## generatePatch diff + censorCells content-blank + CellData read/convert helpers
**Path/Symbol:** `app/server/lib/CellDataAccess.ts` — `CellData.generatePatch` (:300-380), `censorCells` (:382-408), `readCells` (:452-460), `convertToCells` (:486-528), `hasCellInfo` (:464-474), `isAttached` (:479-481), `generateInsert`/`generateUpdate`/`generateRemovals` (:530-604), `getAudience` (:249-283). Consumed by `GranularAccess._filterOutgoingCellInfo` (`app/server/lib/GranularAccess.ts` :2810-2875).
**Signature:** `generatePatch(actions: DocAction[]): DocAction[] | null`; `censorCells(docActions, hasAccess: (cell) => Promise<boolean>): Promise<DocAction[]>` (mutates `colValues.content`/`userRef` in place).
**Data Shape:** a patch is `[insert?, update?, removes?].filter(Boolean)` — one `BulkAddRecord`/`BulkUpdateRecord`/`BulkRemoveRecord` (collapsed to a single action when one id). Censored content is `[GristObjCode.Censored]` with `userRef` blanked to `""`.

### Decisive source
```ts
// generatePatch — collect added/updated/removed cell ids, then expand to cover row updates.
const removedCells = new Set<number>(); const addedCells = new Set<number>(); const updatedCells = new Set<number>();
function applyCellAction(action: DataAction) {
  if (isSomeAddRecordAction(action)) {
    for (const id of getRowIdsFromDocAction(action)) {
      if (removedCells.has(id)) { removedCells.delete(id); updatedCells.add(id); }
      else { addedCells.add(id); }
    }
  } else if (isRemoveRecord(action) || isBulkRemoveRecord(action)) {
    for (const id of getRowIdsFromDocAction(action)) {
      if (addedCells.has(id)) { addedCells.delete(id); }
      else { removedCells.add(id); updatedCells.delete(id); }
    }
  } else {
    for (const id of getRowIdsFromDocAction(action)) {
      if (!addedCells.has(id)) { updatedCells.add(id); }
    }
  }
}
```
```ts
// censorCells — blank content + userRef for cells the user can't read.
if (!isBulkAction(action)) {
  const [, , rowId, colValues] = action;
  const cell = this.getCell(rowId);
  if (!cell || !await hasAccess(cell)) { colValues.content = [GristObjCode.Censored]; colValues.userRef = ""; }
} else {
  const [, , rowIds, colValues] = action;
  for (let idx = 0; idx < rowIds.length; idx++) {
    const cell = this.getCell(rowIds[idx]);
    if (!cell || !await hasAccess(cell)) { colValues.content[idx] = [GristObjCode.Censored]; colValues.userRef[idx] = ""; }
  }
}
```

**Flow:** `generatePatch` first scans the bundle's `_grist_Cells` actions to classify each cell id as added/updated/removed (an add-after-remove becomes an update; an update of an added cell stays added). Then it scans non-cell data actions: a `RenameTable` remaps the updated-rows table key, `RemoveTable` drops it, and any `UpdateRecord`/`BulkUpdateRecord` on a non-`_grist` table marks every cell of that row for refresh (a row update may change metadata visibility). `readCells` then expands each updated row into its cell ids. Finally the three generators emit a single insert/update/removal action each (collapsed to a single action for one id, `null` when empty). `censorCells` walks the patch and blanks `content`→`[GristObjCode.Censored]` and `userRef`→`""` for any cell the `hasAccess` callback rejects (or that no longer exists). `_filterOutgoingCellInfo` uses this: it drops every `isCellDataAction` from the `after` bundle, builds the patch from the `before` bundle, censors it against the user's read access, and appends the censored patch — so the engine's own cell bookkeeping is removed and only the user-readable cells are re-emitted.
**Invariant:** the patch is derived from the BEFORE bundle and censored against the user's read access, then appended to the AFTER bundle — the engine's own `_grist_Cells` actions never reach the client. A censored cell keeps its row/col identity but its `content` becomes the `Censored` code and its `userRef` is blanked (so the client can't infer the author). `readCells` filters by `tableRef` (+ optional `colRef`) and then by `rowId ∈ rowIds` — a porter must keep the rowId filter AFTER the table/col filter.
**Probe:** `test/server/lib/CommentAccess.ts` — "should create proper cell metadata actions" (:572), "should create proper patch with schema actions" (:694), "works across non-trivial bundles" (:797), and "respects private conversation" (:741) pin patch construction and censoring.
**Coverage caveat:** the add-after-remove→update and update-of-added-cell transitions in `applyCellAction` have no isolated unit test; the `Censored`-code emission is pinned indirectly by the private-conversation suite.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "CellData generatePatch censorCells readCells convertToCells hasCellInfo", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the before-derived patch + censor + append-to-after choreography, the add/update/remove cell-id classification with the add-after-remove→update transition, the row-update→cell-refresh expansion, and the `Censored`-code + blanked-`userRef` censoring; adapt the `hasAccess` callback and the metadata table name; omit the comment-thread `getAudience` participant expansion unless you need to surface thread participants.
