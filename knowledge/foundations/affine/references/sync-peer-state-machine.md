<!-- capsule-v2 -->
# SyncPeer connect/pull/push loops — the three concurrent loops and their echo guards

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How does one peer synchronize a Y.Doc (plus subdocs) with one storage without update echo loops, and what must a porter replicate to keep it deadlock-free?

## SyncPeer.sync
**Path/Symbol:** `blocksuite/framework/sync/src/doc/peer.ts`: `SyncPeer.sync()` (:221-326), `connectDoc` (:167-191), `handleYDocUpdates` (:94-111).
**Signature:** `async sync(abortOuter: AbortSignal)`; constructor starts `syncRetryLoop(this.abort.signal)` immediately — a peer is live on construction.
**Data Shape:** state holds three `PriorityAsyncQueue`s (`pushUpdatesQueue` items `{id, data: Uint8Array[]}`, `pullUpdatesQueue` items `{id, data}`, `subdocsLoadQueue` items `{id, doc}`) plus `connectedDocs: Map<guid, Doc>` and two busy flags.

### Decisive source
```ts
// handleYDocUpdates — the ONLY echo guard is the source name vs transaction origin
handleYDocUpdates = (update: Uint8Array, origin: string, doc: Doc) => {
  // don't push updates from storage
  if (origin === this.name) { return; }
  const exist = this.state.pushUpdatesQueue.find(({ id }) => id === doc.guid);
  if (exist) { exist.data.push(update); }   // batch per-doc, never merge here
  else { this.state.pushUpdatesQueue.push({ id: doc.guid, data: [update] }); }
  this.updateSyncStatus();
};
```
```ts
// sync() :273-291 pull loop — empty updates and Uint8Array([0,0]) are skipped
if (!(data.byteLength === 0 || (data.byteLength === 2 && data[0] === 0 && data[1] === 0))) {
  const subdoc = this.state.connectedDocs.get(id);
  if (subdoc) applyUpdate(subdoc, data, this.name);
}
// push loop :294-317 merges each doc's batch then applies the same [0,0] filter
const merged = mergeUpdates(data);
if (!isEmptyShape(merged)) await this.source.push(id, merged);
```

**Flow:** `initState` → `source.subscribe(handleStorageUpdates, disconnect→abortInner.abort)` → Step 1 `connectDoc(rootDoc)`: pull diff, `applyUpdate(doc, docData, 'load')`, enqueue `encodeStateAsUpdate(doc, inStorageState)` as the FIRST push item → Step 2 enqueue existing subdocs + listen `rootDoc.on('subdocs')` → Finally run three infinite loops concurrently: drain subdocsLoadQueue via `connectDoc`, drain pulls into `applyUpdate(...,this.name)`, drain pushes via `mergeUpdates(batch)` → `source.push`.

**Invariant:** (1) Updates applied FROM storage carry origin `this.name`; local Y.Doc transactions carry any other origin — flipping either side creates an infinite echo. (2) The initial push after connect uses `encodeStateAsUpdate(doc, inStorageState)` so only bytes missing from storage are pushed; skipping the vector re-uploads everything and can livelock two peers. (3) `[0,0]`/empty binaries MUST be filtered before push AND before apply — they are valid no-op updates that would still trigger status churn. (4) Loops never exit except by abort; errors propagate to `syncRetryLoop` which resets ALL queues (`initState`) and retries after 5 s — partial queue contents must not survive a retry.

**Probe:** `blocksuite/framework/sync/src/utils/__tests__/async-queue.spec.ts` pins queue wake/batching behavior; the empty-update filter is pinned in source at peer.ts :279-283 and :304-309 (`grep -c "byteLength === 2" doc/peer.ts` == 1 in-tree). No direct SyncPeer unit spec exists (consumer-tested caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "SyncPeer handleYDocUpdates pushUpdatesQueue mergeUpdates", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt origin-echo-guard + per-doc batching + empty-update filtering; adapt the retry backoff and status surface; omit BroadcastChannel-specific transport details.
