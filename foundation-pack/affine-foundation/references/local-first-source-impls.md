<!-- capsule-v2 -->
# IndexedDB + BroadcastChannel doc sources — offline ladder rung and tab-to-tab fanout

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How does the local persistence rung store Yjs updates so any peer can diff against it, and how do sibling tabs hear about writes without a server?

## IndexedDBDocSource.push/pull
**Path/Symbol:** `blocksuite/framework/sync/src/doc/impl/indexeddb.ts`: `push` (:78-101), `pull` (:56-76); `blocksuite/framework/sync/src/doc/impl/broadcast.ts`: `_onMessage` (:17-36).
**Signature:** push appends `{timestamp, update}` rows then compacts; pull merges all rows then diffs.
**Data Shape:** single object-store record per doc `{id, updates: UpdateMessage[]}` where `UpdateMessage = {timestamp: number, update: Uint8Array}`; BroadcastChannel messages `{type:'db-updated', payload:{docId, update}}` / `{type:'update'|'init', docId?, data?}`.

### Decisive source
```ts
// indexeddb.ts push — write-amplification guard: compact as soon as rows reach mergeCount
const { updates } = (await store.get(docId)) ?? { updates: [] };
let rows = [...updates, { timestamp: Date.now(), update: data }];
if (this.mergeCount && rows.length >= this.mergeCount) {
  const merged = mergeUpdates(rows.map(({ update }) => update));
  rows = [{ timestamp: Date.now(), update: merged }];
}
await store.put({ id: docId, updates: rows });
this.channel.postMessage({ type: 'db-updated', payload: { docId, update: data } });
```
```ts
// broadcast.ts constructor — state-sync handshake: newcomers announce, EVERY peer answers with full map
this.channel.postMessage({ type: 'init' });
// _onMessage on receiving 'init':
for (const [docId, data] of this.docMap)
  this.channel.postMessage({ type: 'update', docId, data });
```

**Flow:** push = read-modify-write one row + BroadcastChannel notify; pull = merge all stored updates → `diffUpdate(merged, requesterState)` → also return `encodeStateVectorFromUpdate(merged)` so the caller can push its own missing bytes back. BroadcastChannel source keeps an in-memory `docMap<guid, merged-update>`, merging on every push AND on every inbound message.

**Invariant:** (1) `mergeCount = 1` by default means every push rewrites ONE merged row — a porter raising it must keep the `>=` comparison or rows never compact. (2) The pull response's `state` must come from the MERGED update, not the last row, or peers will skip pushing their unique bytes. (3) The `'init'` handshake is answered by ALL listeners — duplicate answers are safe ONLY because apply-side dedups via Yjs CRDT semantics; filtering them would break convergence after offline divergence. (4) IndexedDB is shared across tabs, so its subscribe uses BroadcastChannel notification rather than re-polling the DB.

**Probe:** `blocksuite/framework/sync/src/__tests__/blob.unit.spec.ts` pins the BlobSource analog of main/shadow propagation (`should sync blobs between main and shadow sources`). Doc-source impls have no direct spec — pinned by `grep -n "mergeCount = 1" blocksuite/framework/sync/src/doc/impl/indexeddb.ts` (:41) and handshake sites :47-49/:18-27.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "IndexedDBDocSource BroadcastChannelDocSource mergeCount init", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append+compact row storage and the init/update channel handshake; adapt store names/versioning to host schema; omit idb dependency if the host has its own KV layer.
