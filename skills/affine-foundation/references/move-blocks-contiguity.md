<!-- capsule-v2 -->
# DocCRUD.moveBlocks — contiguity precheck, per-parent batching, and the insert-index drift rule

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** What are the exact preconditions of a multi-block drag-and-drop move, and why does the insert index increment between source parents?

## DocCRUD.moveBlocks
**Path/Symbol:** `blocksuite/framework/store/src/model/store/crud.ts`: `moveBlocks` (:276-387).
**Signature:** `moveBlocks(blocksToMove: string[], newParent: string, targetSibling: string|null = null, shouldInsertBeforeSibling = true)`.
**Data Shape:** input is an ORDERED id list (visual order); internally grouped into `childBlocksPerParent: Map<sourceParentId, string[]>`; all mutations on `sys:children` Y.Arrays.

### Decisive source
```ts
// precondition trio (:282-302)
if (blocksToMove.length > 1 && targetSibling && blocksToMove.includes(targetSibling)) {
  console.error('Cannot move blocks when the target sibling is in the blocks to move'); return;
}
if (blocksToMove.length === 1 && targetSibling === blocksToMove[0]) return;  // self no-op
if (blocksToMove.includes(newParent)) {
  console.error('Cannot move blocks when the new parent is in the blocks to move'); return;
}
// contiguity check while grouping (:330-338)
const last = children[children.length - 1];
if (this.getNext(last) !== blockId)
  throw new BlockSuiteError(..., 'The blocks to move are not contiguous under their parent');
```
```ts
// index drift correction across multiple source parents (:358-382)
const updateInsertIndex = () => {
  const first = index === 0;
  if (!first) { insertIndex++; return; }        // later groups shift right by one
  if (!targetSibling) { insertIndex = targetParentChildren.length; return; }
  let targetIndex = targetParentChildren.toArray().findIndex(id => id === targetSibling);
  if (targetIndex === -1) { console.error('Target sibling not found, just insert to the end');
    targetIndex = targetParentChildren.length; }
  insertIndex = shouldInsertBeforeSibling ? targetIndex : targetIndex + 1;
};
```

**Flow:** validate trio → group ids per source parent verifying each group is SIBLING-CONTIGUOUS in visual order (throw otherwise — partial moves would corrupt order) → for each source parent: delete the run from its `sys:children`, compute insert index against the target's CURRENT children (after prior deletions), splice in.

**Invariant:** (1) The first group's insert index is computed AFTER that group was removed from its old parent when old parent === new parent (same-parent reorder), but subsequent groups add +1 because earlier inserts shifted positions — recomputing per group instead of caching is what keeps multi-parent moves correct. (2) Contiguity is checked with `getNext` which walks PARENT children arrays — a non-contiguous selection must fail loudly BEFORE any mutation (single transaction via Store.moveBlocks wrapper means CRDT history stays clean). (3) Missing targetSibling degrades to append-with-console-error rather than throw — deliberate UX tolerance at odds with the strict contiguity throw; preserve both behaviors or document divergence. (4) Schema validation of new parent runs per block BEFORE grouping (`this._schema.validate(blockFlavour, parentFlavour)` :319-322).

**Probe:** pinned by source greps: `grep -c "Cannot move blocks" blocksuite/framework/store/src/model/store/crud.ts` == 2 (sibling-in-selection + parent-in-selection guards; the single-block self-move case is a silent no-op return :293-295); throw message :334; Store-level transaction wrapper store.ts :1140-1159 wraps `_crud.moveBlocks` in `transact`. No dedicated unit spec for moveBlocks — consumer-tested caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocCRUD moveBlocks childBlocksPerParent updateInsertIndex contiguous", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the precondition trio + contiguity throw + incremental index rule; adapt error UX; omit only if single-block moves are the product scope.
