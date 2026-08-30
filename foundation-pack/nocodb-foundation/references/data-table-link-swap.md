<!-- capsule-v2 -->
# Copy/paste/deleteAll link swap — how does a cell-level link paste become ONE recorded undoable op instead of N add/remove calls?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you turn a copy→paste (or deleteAll) of a links cell into a computed diff that is deposited for an outer undo scope, applied once, and self-inverse?

## computeListCopyPasteOrDeleteAllDiff + _traceApplyLinkSwap family
**Path/Symbol:** `packages/nocodb/src/services/data-table.service.ts:nestedListCopyPasteOrDeleteAll` (:783-823), `computeListCopyPasteOrDeleteAllDiff` (:829-1051), `_traceApplyLinkSwap` (:1061-1102), `_traceApplyLinkSwapBulk` (:1106-1144), `_traceApplyLinkByDisplay` (:1149-1168), `nestedListBulkCopyPasteOrDeleteAll` (:1170-1236), `nestedBulkLinkByDisplayValue` (:1238-1344).
**Signature:** `private async computeListCopyPasteOrDeleteAllDiff(...): Promise<{ swapEntry: { columnId; rowId; link: pk[]; unlink: pk[] } | null; feResponse: { link: any[]; unlink: any[] } | undefined }>`.
**Data Shape:** Request body is an array of `{operation: 'copy'|'paste'|'deleteAll', rowId, columnId, fk_related_model_id}` entries reduced into an operation map. `swapEntry.link`/`.unlink` are RELATED-TABLE pks.

### Decisive source
```ts
// Deposit the computed diff for an OUTER trace scope (the interface
// page-scoped swap contract builds its inverse from it — its own params
// never carry the diff). No-op when no outer scope is active.
captureForTrace('linkSwapEntry', swapEntry ? { ...swapEntry, rowId: String(swapEntry.rowId) } : null);

if (swapEntry) {
  await this._traceApplyLinkSwap(context, { modelId, viewId, columnId: swapEntry.columnId,
    rowId: swapEntry.rowId, link: swapEntry.link, unlink: swapEntry.unlink, cookie });
}
```
and the apply substrate:
```ts
/** Decorated internal substrate for `recordLinkSwap`. Receives a resolved
 *  (rowId, columnId) link diff ... Self-inverse — undo dispatches the same op
 *  with the link/unlink lists swapped. Higher-level user-facing methods
 *  compute the diff first then funnel through here so the recorded op carries
 *  the resolved pks (replay can't drift). */
@TraceCommand(OperationName.recordLinkSwap)
async _traceApplyLinkSwap(...) {
  if (!param.link.length && !param.unlink.length) return { link: [], unlink: [] };
  ...
  if (param.unlink.length) await baseModel.removeLinks({ colId, childIds: param.unlink, rowId: String(param.rowId), cookie });
  if (param.link.length) await baseModel.addLinks({ colId, childIds: param.link, rowId: String(param.rowId), cookie });
```

**Flow (single cell):** validatePayload → operation map; copy+paste must share fk_related_model_id unless deleteAll → exist() preflight for both rows → column+related model via getParentChildContext → **require `fk_mm_model_id`** (non-junction ⇒ `{swapEntry:null}` no-op) → restrictNestedLinkQuery (same one-bit-oracle closure as nestedDataList — the diff RETURNS matched rows) → mmList both cells → `link = copied − pasted`, `unlink = pasted − copied` (filterAndMapRows compares on ALL primaryKeys by title||column_name, then extractPksValue) → empty diff ⇒ null swapEntry → deposit captureForTrace('linkSwapEntry') → apply once via removeLinks THEN addLinks.
- deleteAll branch: mmList current set → childPks = extractPksValue per row → swapEntry `{link:[], unlink:childPks}`; feResponse returns full ROW objects (not just pks).
- Bulk variants: per-entry diffs accumulate into `linkSwapEntries`; captureForTrace('linkSwapBulkEntries') deposits them; ONE decorated call applies all (`recordLinkSwapBulk`) — inner per-entry calls "auto-skip recording via ALS re-entrancy — only this outer bulk op records".
- By-display bulk (`recordLinkByDisplay`): groups entries by columnId preserving original indexes, resolves display strings → pks via shared two-step resolution, computes per-row diff against mmList of existing links, single recorded op.
**Invariant:** The recorded op must carry RESOLVED pks (never display values or row indices) so undo replay cannot drift; the op is SELF-INVERSE (swap link/unlink lists); removeLinks precedes addLinks; and every entry's `rowId` is stringified before deposit because trace frames stringify ids.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `DataTableService._traceApplyLinkSwap` :1062-1102 exactly; grep counts three `@TraceCommand(OperationName.recordLink*` decorations in this file (Swap / SwapBulk / ByDisplay).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "_traceApplyLinkSwap recordLinkSwap captureForTrace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compute-diff → deposit-for-outer-scope → single-recorded-apply, the resolved-pk replay invariant, and self-inverse undo. Adapt OperationName vocabulary and captureForTrace to your host's command-recording layer. Omit the feResponse row-shape details if your client rebuilds cells itself.
