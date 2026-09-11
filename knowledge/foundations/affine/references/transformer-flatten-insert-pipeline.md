<!-- capsule-v2 -->
# Flatten → convert → rebuild insert pipeline — how do you paste a snapshot tree into a doc without re-entrancy or index drift?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** Why does import flatten the tree first, and in what order must parent/index be computed so a subtree lands at the requested position?

## Three-phase pipeline with batched yields
**Path/Symbol:** `blocksuite/framework/store/src/transformer/transformer.ts:490-502` (`_flattenSnapshot`), :413-441 (`_convertFlatSnapshots`), :571-604 (`_rebuildBlockTree`), :522-569 (`_insertBlockTree`).
**Signature:** `_flattenSnapshot(snapshot, flatSnapshots[], parentId?, index?)`; `_insertBlockTree(nodes, doc, parentId?, startIndex?, counter = 0): Promise<number>`.
**Data Shape:** `FlatSnapshot = { snapshot, parentId?, index? }` — a DFS pre-order list where every node records the id of its parent and its child position.

### Decisive source
```ts
// transformer.ts:496-500 — children indexed by ORIGINAL sibling order
flatSnapshots.push({ snapshot, parentId, index });
if (snapshot.children) {
  snapshot.children.forEach((child, idx) => {
    this._flattenSnapshot(child, flatSnapshots, snapshot.id, idx);
  });
}

// transformer.ts:553-555 — cooperative yield every 100 inserts
counter++;
if (counter % BATCH_SIZE === 0) {   // const BATCH_SIZE = 100;  // :55
  await nextTick();
}
```

**Flow:** `_snapshotToBlock` (:606) → `_triggerBeforeImportEvent` walks tree firing block-level slots with parent/index context (:624-647) → `_flattenSnapshot` → Phase 1 serial `fromSnapshot` per node (comment at :415: "faster than Promise.all"; each failure logs + drops that node) → Phase 2 filter nulls → Phase 3 `_rebuildBlockTree` two passes (id→node map, then attach each node to `parentNode.children[index]`) → `_insertBlockTree` walks the rebuilt tree calling `doc.addBlock(flavour, { id, ...props }, parentId, actualIndex)` where `actualIndex = startIndex + index` only at top level (:534-536); children recurse with `index=undefined` so append-order is preserved.
**Invariant:** (1) The flat list must be DFS PRE-ORDER — `_rebuildBlockTree` reads `draftModels[0].draft.id` as root (:584), so any other order reparents the tree. (2) `actualIndex` arithmetic applies ONLY to the entry-level siblings; deeper levels rely on recursion appending in order. (3) `nextTick()` yield keeps the UI responsive during large pastes — dropping it freezes main thread for 1000-block docs.
**Probe:** `grep -n '_flattenSnapshot' …transformer.ts | cut -d: -f1` → `271 490 499 615`. And `grep -n 'nextTick()\|BATCH_SIZE = \|temporary-root\|hasBlock(first.id)' …transformer.ts | cut -d: -f1` → `55 260 277 554`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "Transformer _convertFlatSnapshots draft models phase rebuild block tree", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flatten/convert/rebuild/insert pipeline verbatim for any snapshot→tree importer. Adapt BATCH_SIZE to your frame budget. Omit Promise.all conversion — serial awaits are deliberate (asset hooks may mutate shared state).
