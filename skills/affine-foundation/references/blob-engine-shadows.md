<!-- capsule-v2 -->
# BlobEngine — content-addressed set() with fire-and-forget shadow fanout and list-diff sync

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How are binary blobs replicated across storages without blocking writes, and why can nothing ever be deleted?

## BlobEngine.set / sync / delete
**Path/Symbol:** `blocksuite/framework/sync/src/blob/engine.ts`: `set` (:59-105), `sync` (:145-204), `delete` (:29-33), `start` (:115-138).
**Signature:** `set(valueOrKey: string | Blob, _value?: Blob): Promise<string>` (overloads: key optional — sha256 of content when omitted); `sync(): Promise<void>` runs every 60 s from `start()`.
**Data Shape:** `BlobSource { name, readonly, get, set(key, value)→key, delete, list→string[], blobState$?, upload? }`; keys are hex sha256 of blob bytes.

### Decisive source
```ts
// await MAIN only; shadows replicate in background and failures are logged, not thrown
await this.main.set(key, value);
Promise.allSettled(
  this.shadows.filter(r => !r.readonly).map(peer =>
    peer.set(key, value).catch(err => this.logger.error('Error when uploading to peer', err))
  )
).then(result => {
  if (result.some(({ status }) => status === 'rejected'))
    this.logger.error(`blob ${key} update finish, but some peers failed to update`);
});
return key;   // caller unblocked immediately after main ack
```
```ts
async delete(_key: string) {
  this.logger.error('You are trying to delete a blob. We do not support this feature yet. ...');
}
```
```ts
// periodic reconciliation is a plain bidirectional LIST DIFF
const needUpload = mainList.filter(key => !shadowList.includes(key));
... const needDownload = shadowList.filter(key => !mainList.includes(key));
```

**Flow:** `set` → compute/validate key → await main → schedule background shadow uploads → return key. Every 60 s `start()`'s loop reconciles each writable shadow against main via list-diff in BOTH directions (download fills main gaps too). `get` walks `[main, ...shadows]` first-hit wins; `list` unions all sources into a Set.

**Invariant:** (1) Keys are content hashes — two blobs with the same key are assumed identical, which is exactly what makes fire-and-forget replication and last-write-anywhere safe. (2) Delete is intentionally a logged NO-OP until an indexer can prove no doc references the key — porting "just add delete" reintroduces dangling-reference corruption. (3) Shadow upload failure leaves convergence to the next 60 s sweep; there is no retry queue, so `readonly` shadows are filtered BEFORE upload but still contribute downloads. (4) `main.readonly ⇒ throw` on set — main is the write authority even though get falls through to shadows.

**Probe:** `blocksuite/framework/sync/src/__tests__/blob.unit.spec.ts` :26-33 pins main→shadow propagation via explicit `engine.sync()`; :44-50 pins delete-is-no-op (`retrievedBlob).not.toBeNull()`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "BlobEngine set sync needUpload needDownload readonly", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt content-addressed keys, await-main/fanout-shadows, and list-diff reconciliation; adapt the 60 s interval and error surface; omit delete only WITH the same reference-indexer precondition.
