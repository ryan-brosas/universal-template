<!-- capsule-v2 -->
# Slice paste move-vs-insert fork — when does pasting a slice MOVE existing blocks instead of duplicating them?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** How does slice import decide between inserting fresh blocks and relocating ones already in the doc (drag-within-page), and what is the temporary-root trick for?

## `snapshotToSlice` with temporary root + hasBlock fork
**Path/Symbol:** `blocksuite/framework/store/src/transformer/transformer.ts:242-319` (`snapshotToSlice`); tmp root :258-265; fork :277-294.
**Signature:** `snapshotToSlice(snapshot: SliceSnapshot, doc: Store, parent?: string, index?: number): Promise<Slice | undefined>`.
**Data Shape:** Input content = top-level `BlockSnapshot[]` only — children of each entry ride inside their snapshots.

### Decisive source
```ts
// transformer.ts:259-265 — synthetic envelope makes top-level entries uniform
const tmpRootSnapshot: BlockSnapshot = {
  id: 'temporary-root',
  flavour: 'affine:page',     // must be a REGISTERED flavour or _getSchema throws
  props: {},
  type: 'block',
  children: content,
};
...
// transformer.ts:277-291 — already-in-doc ⇒ MOVE, never duplicate
if (first && doc.hasBlock(first.id)) {
  const models = content.map(b => doc.getBlock(b.id)?.model).filter(Boolean);
  const parentModel = parent ? doc.getBlock(parent)?.model : undefined;
  if (!parentModel) {
    throw new BlockSuiteError(ErrorCode.TransformerError,
      'Parent block not found in doc when moving slice');
  }
  const targetSibling = index !== undefined ? parentModel.children[index] : null;
  doc.moveBlocks(models, parentModel, targetSibling);
} else {
  await this._insertBlockTree(blockTree.children, doc, parent, index);
}
```

**Flow:** parse schema → beforeImport slot → wrap content under `temporary-root` → `_triggerBeforeImportEvent` per top-level block → flatten/convert/rebuild → **fork**: first block id exists in doc ⇒ move path (`moveBlocks` with optional insert-before sibling); else insert path. Then rebuilds the returned `Slice` from live models via `doc.getModelById(tree.draft.id)` and fires afterImport.
**Invariant:** (1) The move fork keys on the FIRST block's id alone — a slice whose head exists but tail is new moves only what's found (`.filter(Boolean)` silently shrinks). (2) Move path requires an explicit `parent` that resolves, else throws `'Parent block not found in doc when moving slice'` — there is no default-parent fallback. (3) The temporary root itself is NEVER inserted into the doc; it exists only so flatten/rebuild treat top-level entries as a uniform tree. Its flavour must resolve through `_getSchema`, so `'affine:page'` (registered in every real app) is load-bearing.
**Probe:** `grep -n 'temporary-root\|hasBlock(first.id)' …transformer.ts | cut -d: -f1` → `260`, `277`. And `grep -n "Parent block not found" …transformer.ts` → single site :286 (the move-fork throw).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "snapshotToSlice temporary root move blocks target sibling", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hasBlock-first-id fork for any paste/drop importer — it is what makes dragging a block across a page move rather than clone it. Adapt the sentinel id/flavour to your own registered root flavour. Omit the filter(Boolean)-shrink at your peril: decide explicitly whether a half-present slice should move partially or abort.
