<!-- capsule-v2 -->
# DocSource — what a storage backend must honor for the sync engine to be correct

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** What is the exact contract a pluggable doc storage must satisfy (pull/push/subscribe semantics) so SyncPeer stays correct, and where does the engine assume the storage deduplicates?

## DocSource triple
**Path/Symbol:** `blocksuite/framework/sync/src/doc/source.ts`: `DocSource` (:1-28).
**Signature:**
```ts
interface DocSource {
  name: string;
  pull(docId, state): Promise<{ data; state? } | { data; state? } | null> | ... | null;
  push(docId, data): Promise<void> | void;
  subscribe(cb: (docId, data) => void, disconnect: (reason: string) => void):
    Promise<() => void> | (() => void);
}
```
**Data Shape:** `state` is the requester's Yjs state vector (`Uint8Array`); `data` is a binary update diff; `pull` returns `null` when the storage has never seen `docId`; `subscribe` returns an unsubscribe function and MUST invoke `disconnect(reason)` when the transport dies.

### Decisive source
```ts
// indexeddb.ts — pull diffs against the caller's state vector
const update = mergeUpdates(updates.map(({ update }) => update));
const diff = state.length ? diffUpdate(update, state) : update;
return { data: diff, state: encodeStateVectorFromUpdate(update) };
```
```ts
// peer.ts :66-72 — every storage callback lands on ONE pull queue; ordering is FIFO per queue
handleStorageUpdates = (id: string, data: Uint8Array) => {
  this.state.pullUpdatesQueue.push({ id, data });
  this.updateSyncStatus();
};
```

**Flow:** connect → `pull(guid, encodeStateVector(doc))` → apply returned `data` with origin `'load'` (so it is not re-pushed) → push local-only diff back → `subscribe(cb, disconnect)` feeds later remote updates into the pull loop. The engine itself never merges concurrent remote updates before apply — each queued item is applied as-is with `applyUpdate(subdoc, data, this.name)`.

**Invariant:** `pull`'s returned `data` must be exactly the missing set between `state` and storage content (implementations use `diffUpdate(update, state)`); returning full state instead only wastes bytes but returning *stale* state breaks convergence because the peer trusts the vector in `state`. The `name` string doubles as the transaction-origin marker that suppresses echo loops — two sources sharing a name silently drop updates.

**Probe:** `blocksuite/framework/sync/src/__tests__/blob.unit.spec.ts` exercises the BlobSource twin of this contract; the DocSource shape is pinned by `doc/impl/noop.ts`, `impl/indexeddb.ts`, and `impl/broadcast.ts` all satisfying it (no direct unit spec for DocSource itself — caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocSource IndexedDBDocSource pull subscribe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-method source interface plus state-vector diffing on pull; adapt persistence behind it (IndexedDB/BroadcastChannel are reference impls); omit the browser BroadcastChannel transport when porting to server contexts.
