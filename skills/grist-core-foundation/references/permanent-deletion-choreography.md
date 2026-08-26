<!-- capsule-v2 -->
# Permanent deletion choreography — how do you delete a document across DB rows, storage, forks, and caches without orphaning any layer?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** In what ORDER must soft-delete, attachment-pool cleanup, fork enumeration, storage deletion, DB deletion, auth-cache flush, and client interruption run?

## De-list first, clean remotes before content, flush auth cache + interrupt clients LAST
**Path/Symbol:** `app/server/lib/DocApi.ts:_removeDoc` (:1864–1903); helpers `parseUrlId`/`buildUrlId` (gristUrls), `getDocPoolIdFromDocInfo` (AttachmentStore); callers DELETE `/docs/:docId` (:899–902) and POST `/remove?permanent=` (:907–917).
**Signature:** `_removeDoc(req, res, permanent: boolean): Promise<QueryResult<Document>>`.
**Data Shape:** fork docs carry `forkId` in their urlId; trunks enumerate forks via `dbManager.getDocForks(docId)` and rebuild each full urlId with `buildUrlId({forkId, forkUserId: createdBy!, trunkId})`.

### Decisive source
```ts
if (permanent) {
    const { forkId } = parseUrlId(docId);
    if (!forkId) {
      // Soft delete the doc first, to de-list the document.
      await this._dbManager.softDeleteDocument(scope);
    }
    const forks = forkId ? [] : await this._dbManager.getDocForks(docId);
    const docsToDelete = [docId,
      ...forks.map(f => buildUrlId({ forkId: f.id, forkUserId: f.createdBy!, trunkId: docId }))];
    if (!forkId) {
      // Delete all remote document attachments BEFORE the doc itself.
      // This way we can re-attempt deletion if an error is thrown.
      const stores = await this._attachmentStoreProvider.getAllStores();
      await Promise.all(stores.map(s => s.removePool(getDocPoolIdFromDocInfo({ id: docId, trunkId: null }))));
    }
    await Promise.all(docsToDelete.map(n => this._docManager.deleteDoc(null, n, true)));
    result = await this._dbManager.deleteDocument(scope);   // DB row LAST
    this._dbManager.checkQueryResult(result);
} else {
    result = await this._dbManager.softDeleteDocument(scope);
}
await this._dbManager.flushSingleDocAuthCache(scope, docId);   // always, both paths
await this._docManager.interruptDocClients(docId);
```
**Flow:** soft-delete de-lists BEFORE anything destructive (concurrent viewers see "removed", not partial content) → trunk case enumerates ALL forks into explicit urlIds → remote attachment pools removed first (idempotent-ish, re-attemptable) → per-doc storage deletion fans out in parallel → home-DB row deleted and query-result checked → FINALLY (both permanent and soft paths) flush the single-doc auth cache so stale ACLs can't resurrect access, and interrupt connected clients so open sessions learn immediately.
**Invariant:** deleting a trunk deletes its forks; deleting a fork never touches attachments pool cleanup (`if (!forkId)` guard) because pools are trunk-scoped. Remote-before-local ordering exists purely for retryability: a crash after storage cleanup leaves a de-listed, re-deletable doc; the reverse orphans blobs forever. Auth-cache flush is NOT optional on soft-delete — removal changes access semantics immediately.
**Probe:** `test/server/lib/docapi/DocApiDocuments.ts` (delete/remove endpoints suite); coverage caveat: the ordering rationale ("This way we can re-attempt…") is an in-source comment; suites assert outcomes, not order.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_removeDoc softDeleteDocument deleteDocument getDocForks removePool flushSingleDocAuthCache interruptDocClients", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the de-list→remotes→content→DB-row→cache-flush→notify ordering for any multi-layer deletion. Adapt pool/fork concepts to your resource tree. Omit fork enumeration only when your documents have no derivative copies.
