<!-- capsule-v2 -->
# Notebook cell-operations reducer — how do you apply a batch of insert/replace/delete/move ops to an ordered document with conflict detection and diff-noise reduction?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What is the exact shape of a pure, batched, order-dependent cell-edit reducer that (a) rejects conflicting op batches before any mutation, (b) resolves anchors against the MOVING working list, and (c) reports a per-cell diff where canceling moves produce zero "moved" badges?

## Operation grammar + error taxonomy (`data/content/notebooks/notebook-operations.ts`)
**Path/Symbol:** `apps/studio/data/content/notebooks/notebook-operations.ts` : `CELL_ANCHOR_START` (:10), op schemas (:12-44), `NotebookOperationError` (:61-65), `describeNotebookOperationError` (:86-95).
**Signature:** `notebookOperationSchema = z.discriminatedUnion('_tag', [insert_cell, replace_cell, delete_cell, move_cell])`; cells in ops come from `agentCellSchema` — which has NO `_id` field at all (agents cannot write ids; see the wire/draft-id capsule).
**Data Shape:** four ops keyed by `_tag`: `insert_cell { after_cell_id, cell }` (anchor `'start'` = beginning), `replace_cell { cell_id, cell }`, `delete_cell { cell_id }`, `move_cell { cell_id, after_cell_id }`. Error tags: `unknown_cell_id { cell_id }`, `conflicting_operations { cell_id }`, `empty_result {}` — each mapped to a human-readable sentence by `describeNotebookOperationError` (the LLM-facing message layer).

### Decisive source
```ts
export type NotebookOperationError =
  | { _tag: 'unknown_cell_id'; cell_id: string }
  | { _tag: 'conflicting_operations'; cell_id: string }
  | { _tag: 'empty_result' }

export function describeNotebookOperationError(error: NotebookOperationError): string {
  switch (error._tag) {
    case 'unknown_cell_id':
      return `No cell with id "${error.cell_id}" exists in this notebook.`
    case 'conflicting_operations':
      return `More than one operation targets cell "${error.cell_id}".`
    case 'empty_result':
      return 'This update would leave the notebook with no cells.'
  }
}
```

**Flow:** a caller (the agent tool path) submits an ordered op list; the reducer either returns the full resulting document or ONE typed error naming the offending cell id — never a partial application.
**Invariant:** the error set must be closed and machine-discriminable (`_tag` union) so an agent can react to it; the human description is a separate pure function over that union, not embedded in the error values.
**Probe:** `notebook-operations.test.ts` (pure vitest, 521L, read whole; unexecutable in-lane — standing block) pins all three error tags with exact object equality.

## Conflict pre-pass + anchor resolution on the moving list
**Path/Symbol:** same file : `deriveNotebookDiff` (:165-276), `targetCellId` (:97-106), `findAnchorIndex` (:108-121), `findTargetCell` (:123-133), `insertAfter` (:187-201).
**Signature:** `deriveNotebookDiff(notebook: NotebookWire, operations: NotebookOperation[]): DeriveNotebookDiffResult`.
**Data Shape:** the pre-pass collects every targeted `cell_id` into a Set BEFORE any op runs — a second op targeting the same id returns `conflicting_operations` immediately. Consequence pinned by test: a replaced cell can be ANCHORED on (insert/move after it) but never TARGETED again. Anchors resolve through `findAnchorIndex`: unchanged/moved entries match by cell id, replaced entries match by `before._id`, added/removed entries are NEVER anchors. `insertAfter` keeps an `insertedAfter: Map<anchor, count>` offset so multiple inserts anchored at the same cell preserve operation order (splice index = anchorIndex + 1 + offset).

### Decisive source
```ts
const targetedIds = new Set<string>()
for (const operation of operations) {
  const cellId = targetCellId(operation)
  if (cellId === undefined) continue
  if (targetedIds.has(cellId)) {
    return { success: false, error: { _tag: 'conflicting_operations', cell_id: cellId } }
  }
  targetedIds.add(cellId)
}
// ...
const insertAfter = (anchor: string, entry: NotebookCellDiffEntry) => {
  const anchorIndex = anchor === CELL_ANCHOR_START ? -1 : findAnchorIndex(entries, anchor)
  if (anchor !== CELL_ANCHOR_START && anchorIndex === -1) {
    return { _tag: 'unknown_cell_id', cell_id: anchor }
  }
  const offset = insertedAfter.get(anchor) ?? 0
  entries.splice(anchorIndex + 1 + offset, 0, entry)
  insertedAfter.set(anchor, offset + 1)
  return undefined
}
```

**Flow:** working list starts as all-`unchanged` entries; ops apply IN ORDER against the moving list — a move anchored on another moved cell resolves at its NEW position (test-pinned both orderings give different results: order matters). `move_cell` = splice-out then `insertAfter`; moving a cell after itself is `conflicting_operations`. All-removed ⇒ `empty_result`. `fromIndex` on moved entries is captured from the ORIGINAL notebook order, not the shifted working order (test-pinned).
**Invariant:** batch semantics are ORDER-DEPENDENT and CONFLICT-FREE by construction: the pre-pass makes "two writers touching one cell" unrepresentable as a success, and anchor resolution against the moving list (not the original) is what makes chained moves composable. A porter who resolves anchors against the original snapshot silently breaks move-after-move sequences.
**Probe:** the 521L test suite pins: same-anchor multi-insert ordering, move-on-moved both orders, canceling moves returning to original order, anchor-on-replaced accepted / target-after-replaced rejected, fromIndex-vs-original, removed entries not disturbing same-anchor inserts.

## No-op-move downgrade + result projection
**Path/Symbol:** same file : `downgradeNoOpMoves` (:135-163), `resultingCells` (:278-291), `applyNotebookOperations` (:293-307).
**Signature:** `applyNotebookOperations(notebook, operations): ApplyNotebookOperationsResult` = `{ success: true, notebook: { schema_version, cells } } | { success: false, error }`.
**Data Shape:** diff entries are five-tagged: unchanged / added{operationIndex} / removed{operationIndex} / replaced{before, after, operationIndex} / moved{fromIndex, operationIndex}. The downgrade compares each moved cell's SURVIVING-cell predecessor SET in the final order against its original predecessor list (length-equal + every original predecessor present); equal ⇒ the move canceled out ⇒ entry becomes `unchanged`.

### Decisive source
```ts
const hasSamePredecessors = (cellId: string) => {
  const finalPredecessors = new Set(finalOrder.slice(0, finalOrder.indexOf(cellId)))
  const originalPredecessors = originalOrder.slice(0, originalOrder.indexOf(cellId))
  return (
    originalPredecessors.length === finalPredecessors.size &&
    originalPredecessors.every((predecessor) => finalPredecessors.has(predecessor))
  )
}
return entries.map((entry) =>
  entry._tag === 'moved' && hasSamePredecessors(entry.cell._id)
    ? { _tag: 'unchanged', cell: entry.cell }
    : entry
)
```

**Flow:** `deriveNotebookDiff` runs the ops, checks empty_result, then downgrades; `applyNotebookOperations` projects entries to plain cells (removed drops out, replaced yields `after`). The predecessor-set comparison is relative to SURVIVING cells only — deletions elsewhere don't create false "moved" badges.
**Invariant:** a diff badge means "this cell's neighborhood actually changed" — two moves that cancel out must produce zero moved badges or downstream UI/agent consumers will report phantom churn. Index-based comparison would be wrong here because intervening inserts/deletes shift indices; the predecessor SET is the shift-invariant notion of position.
**Probe:** test-pinned: canceling moves ⇒ all-unchanged entries; genuinely reordering moves keep their badges; deleted-cell-in-the-middle does not disturb same-anchor insert ordering.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "deriveNotebookDiff applyNotebookOperations downgradeNoOpMoves insertAfter NotebookOperation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full pattern for any ordered-document edit API driven by an LLM or remote client: closed `_tag` op union over id-less payload cells, pre-pass conflict detection (one target per op batch), anchor resolution against the moving working list with an insertedAfter offset map, typed closed error union + separate human-description function, empty-result guard, and predecessor-set no-op-move downgrade for diff consumers. Adapt the `'start'` sentinel and the five-tag diff to your document model. Omit nothing structural — the order-dependence and conflict-free guarantees are the point; if you need commutative ops, you need a different design (CRDT), not this reducer.
