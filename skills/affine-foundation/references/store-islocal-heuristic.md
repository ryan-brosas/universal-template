<!-- capsule-v2 -->
# Store._handleYEvent — the isLocal heuristic and why undo/remote both count as "local"

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How does the block store classify a Yjs transaction as local vs remote, and what are the consequences for UI event streams?

## Store._handleYEvent
**Path/Symbol:** `blocksuite/framework/store/src/model/store/store.ts`: `_handleYEvent` (:1266-1293).
**Signature:** private; subscribed via `yBlocks.observeDeep(this._handleYEvents)` in the constructor (:598), removed in `dispose()` (:1247) only when `doc.ready`.
**Data Shape:** events arrive as `Y.YEvent[]` on the TOP-LEVEL block map only; payload `{type:'add'|'delete', id, isLocal}` forwarded on `slots.yBlockUpdated`.

### Decisive source
```ts
private _handleYEvent(event) {
  // event on top-level block store
  if (event.target !== this._yBlocks) return;          // prop-level changes ignored here
  const isLocal =
    !event.transaction.origin ||                       // no origin  -> local
    !this._yBlocks.doc ||
    event.transaction.origin instanceof Y.UndoManager ||// undo/redo  -> local
    event.transaction.origin.proxy                     // proxy-tagged -> local
      ? true
      : event.transaction.origin === this._yBlocks.doc.clientID;
  event.keys.forEach((value, id) => {
    if (value.action === 'add')    this._handleYBlockAdd(id, isLocal);
    if (value.action === 'delete') this._handleYBlockDelete(id, isLocal);
  });
}
```

**Flow:** observeDeep fires for nested changes too, but this handler filters to `event.target === yBlocks` (block add/delete at map level). Each added id → `_onBlockAdded(id, isLocal, init)` which constructs a Block/SyncController, runs query, emits `rootAdded` when role==='root' and `blockUpdated add`; each deleted id → `_onBlockRemoved`. The same ternary heuristic is duplicated in SyncController (:45-51), BaseReactiveYData (:34-40), Text (:83-89), and Boxed (:121-127) — four sites must stay in agreement.

**Invariant:** (1) UndoManager-origin transactions are classified LOCAL even though they revert remote content — consumers get `isLocal:true` for undo of a peer's insert. (2) SyncPeer applies storage updates with origin `source.name` (a string ≠ clientID), so remote loads correctly report `isLocal:false`; any port that applies with `undefined` origin misclassifies them local. (3) Prop-level (`prop:*`) events never pass through this handler — they are handled per-block by SyncController's observer; adding block-level handling for them double-fires events.

**Probe:** `grep -c "instanceof Y.UndoManager" blocksuite/framework/store/src/model/store/store.ts blocksuite/framework/store/src/model/block/sync-controller.ts blocksuite/framework/store/src/reactive/base-reactive-data.ts` — ≥1 each (four-site duplication). Constructor wiring pinned at :598 (`observeDeep`) and dispose pairing :1247.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "_handleYEvent isLocal observeDeep yBlockUpdated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-clause heuristic verbatim (including its surprises); adapt slot naming; consolidate the duplicated ternary into ONE helper if porting to reduce drift risk.
