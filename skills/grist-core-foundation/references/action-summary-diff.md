<!-- capsule-v2 -->
# ActionSummary — how do you express "what changed" so summaries can be composed across history windows?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What data shape captures net table/column/row/cell changes with renames and bulk-truncation, such that two summaries can be merged into one truthful summary?

## Net-change tree with [before,after] name pairs and '?' unknown cells
**Path/Symbol:** `app/common/ActionSummary.ts:ActionSummary/TableDelta/ColumnDelta` (80–119) + contract doc (6–75); producer `app/common/ActionSummarizer.ts:summarizeStoredAndUndo` (259–298), `_addRows` truncation (208–231); composer `concatenateSummaryPair` (605–613), `planNameMerge` (318–375), `mergeColumn` (483–526), `mergeTable` (554–602).
**Signature:** `concatenateSummaryPair(sum1: ActionSummary, sum2: ActionSummary): ActionSummary`; `addForwardAction(summary, act)` / `addReverseAction(summary, act)`.
**Data Shape:** `tableRenames: LabelDelta[]` where `LabelDelta = [string|null, string|null]` (null = creation/deletion; deleted tables keyed `-Name` via `defunctTableName`); `TableDelta = { updateRows, removeRows, addRows: number[], columnDeltas: {[colId]: {[rowId]: CellDelta}}, columnRenames, mayBeIncomplete? }`; `CellDelta = [[before], [after]]` with `'?'` marking a known-touched-unknown-value cell.

### Decisive source
```ts
// Bulk actions over maximumInlineRows keep only first N-1 rows + last row as samples:
if (limitRows) {
  selectedRows = [...rowIds.slice(0, this._maxRows - 1).entries()];
  selectedRows.push([rowIds.length - 1, rowIds[rowIds.length - 1]]);
  td.mayBeIncomplete = true;                       // ← consumers must now treat gaps as UNKNOWN
}
// Composition default is [v1[0], v2[1]], but a side whose summary is complete may
// recover the true value for an untouched column instead of keeping '?':
const v1Untouched = v1 === undefined && !incomplete1;
const pre  = (v1Untouched && v1[0] === "?") ? v2[0] : v1[0];
const post = (v2Untouched && v2[1] === "?") ? v1[1] : v2[1];
// Rows added AND removed within the window are transients — erased from history:
const transients = e1.addRows.filter(x => removeRows2.has(x));
```

**Flow:** per action bundle: forward stored actions fill new values (`cell[1]=[value]`); REVERSED undo actions fill old values (`cell[0]=[value]`); after the pass, rename lists are replayed so every delta lives under its ULTIMATE table/column name and row-id sets are deduped. Composition merges pairwise left→right: `planNameMerge` aligns both sides' name changes (handles add+delete cancelling, delete-then-recreate exposing `-N` history, renames chains), rekeys deltas to final names via cache-out/rename-in (names can be swapped/shuffled), then `mergeColumn` stitches cells with the untouched-vs-truncated distinction governed by `mayBeIncomplete`, and `mergeTable` drops transient rows entirely.
**Invariant:** only NET changes survive — done-and-undone edits vanish, intermediate states vanish; missing columnDeltas entry means "column untouched" ONLY while `mayBeIncomplete` is unset, otherwise it's ambiguous ('?' semantics); rowIds have no identity across remove+add (same id may be unrelated rows) which is exactly what addRows/removeRows membership disambiguates; `_grist_*` metadata tables are never truncated (always fully summarized).
**Probe:** `test/server/lib/ActionSummary.ts` (whole-file suite: summarization of forward/reverse pairs, composition incl. renames/transients/bulk '?', rebase cases); `app/common/ActionSummary.asTabularDiffs` rendering pinned by client-side tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "ActionSummary concatenateSummaryPair planNameMerge", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape + composition algebra whenever you need auditable change-feeds over action logs (history panels, webhook payloads, incremental sync): LabelDelta naming, defunct `-name` keys, sampled-bulk with explicit incompleteness flag, and merge that respects it. Adapt inline-row thresholds and whether you need the rebase (`rebaseSummary`) half. Omit TabularDiff rendering unless building UI.
