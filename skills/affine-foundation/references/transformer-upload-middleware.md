<!-- capsule-v2 -->
# uploadMiddleware — how do async blob uploads attach to blocks that may be re-created mid-upload?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** How is an upload lifecycle kept race-free when the block it targets can be deleted and re-added (id replaced) during the upload?

## View-driven re-arm loop with abort + withoutTransact commit
**Path/Symbol:** `blocksuite/affine/shared/src/adapters/middlewares/upload.ts:12-118` (`uploadMiddleware`); race :43-70; view subscription :86-113.
**Signature:** `uploadMiddleware(std: BlockStdScope, concurrent = 5): TransformerMiddleware`.
**Data Shape:** Consumes `assetsManager.uploadingAssetsMap: Map<blockId, { blob, abortController?, mapInto }>` — populated by importers BEFORE the block exists.

### Decisive source
```ts
// upload.ts:43-58 — sha-addressed store, then a transaction-scoped prop write
const blobId = await Promise.race([
  (async function processUpload() {
    const blobId = await sha(await blob.arrayBuffer());
    assetsManager.getAssets().set(blobId, blob);
    await assetsManager.writeToBlob(blobId);
    return await new Promise<string | null>(resolve => {
      model.store.withoutTransact(() => {
        if (signal.aborted) return resolve(null);
        model.store.updateBlock(model, mapInto(blobId));
        resolve(blobId);
      });
    });
  })(),
  new Promise<null>(resolve => {          // abort arm resolves null
    signal.addEventListener('abort', () => resolve(null), { once: true });
    if (signal.aborted) resolve(null);
  }),
]);
```

**Flow:** importer puts `{blob, abortController}` into `uploadingAssetsMap` keyed by EXPECTED block id → middleware subscribes to `std.view.viewUpdated` filtered to `'block'` events on flavours `{'affine:image','affine:attachment'}` → on `'add'` method for a watched id it ARMS a fresh AbortController and starts `upload(...)` through `mergeMap(…, concurrent=5)`; on any other method (delete/replace) it aborts + dequeues. Upload itself: content-hash the blob (sha = dedupe key), stash in assets map, persist via blobCRUD, then write props INSIDE `withoutTransact` (the resulting history entry doesn't pollute undo as a user edit).
**Invariant:** (1) The add→upload handshake tolerates id replacement because replaceIdMiddleware re-keys `uploadingAssetsMap` before this middleware sees the new id. (2) `withoutTransact` around `updateBlock` is what keeps uploads out of the undo stack — dropping it makes every paste-with-image an undoable step. (3) Concurrency cap lives in mergeMap; failures log-and-drop (`console.error` + delete from map) — there is NO retry.
**Probe:** `grep -n 'concurrent = 5\|mergeMap(\|withoutTransact\|throwIfAborted' …middlewares/upload.ts | cut -d: -f1` → `14 54 102` (and throwIfAborted at :38). And `grep -c 'Subscription = ' …upload.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "uploadMiddleware uploadingAssetsMap abort signal mergeMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt expect-then-attach with abort arms for any async resource landing on volatile ids. Adapt the view-event source to your framework's mount events. Omit withoutTransact at the cost of undo pollution; omit the sha pre-hash and you lose free server-side dedupe.
