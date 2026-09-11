<!-- capsule-v2 -->
# Debounced store pipeline — how does a CRDT doc become a relational row without write storms or lost side effects?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** What is the exact order of operations when hocuspocus flushes a Y.Doc to Postgres, and which steps are skipped on a no-op save?

## PersistenceExtension.onStoreDocument
**Path/Symbol:** `apps/server/src/collaboration/extensions/persistence.extension.ts`:`onStoreDocument` (lines 98–218).
**Signature:** `onStoreDocument(data: onStoreDocumentPayload): Promise<void>`; store cadence set by gateway config `debounce: 10000, maxDebounce: 45000, unloadImmediately: false`.
**Data Shape:** Writes THREE derived artifacts per save — `content` (tiptap JSON via `TiptapTransformer.fromYdoc(doc,'default')`), `ydoc` (binary `Y.encodeStateAsUpdate` as Buffer), `textContent` (flattened text, best-effort, null on conversion error).

### Decisive source
```ts
const tiptapJson = TiptapTransformer.fromYdoc(document, 'default');
const ydocState = Buffer.from(Y.encodeStateAsUpdate(document));
await executeTx(this.db, async (trx) => {
  page = await this.pageRepo.findById(pageId, { withLock: true, includeContent: true, trx });
  if (!page) return;
  if (isDeepStrictEqual(tiptapJson, page.content)) { page = null; return; }  // no-op save
  await this.pageRepo.updatePage({ content: tiptapJson, textContent, ydoc: ydocState, lastUpdatedById: lastContext.user.id, contributorIds }, pageId, trx);
});
if (page) {
  document.broadcastStateless(JSON.stringify({ type: 'page.updated', ... }));
  await this.syncTransclusion(pageId, page.workspaceId, tiptapJson);   // isolated, failure-tolerant
  await this.collabHistory.addContributors(pageId, editingUserIds);
  /* mention diff → notificationQueue; PAGE_CONTENT_UPDATED → aiQueue; enqueuePageHistory(page) */
}
```

**Flow:** debounced trigger → derive JSON + binary state → row-locked tx → deep-equal short-circuit (page=null) → update → ONLY IF changed: broadcastStateless `page.updated`, transclusion sync (each half individually caught), contributor merge into Redis, mention-diff notifications, AI reindex job, history enqueue.
**Invariant:** the `page === null` sentinel after `isDeepStrictEqual` gates EVERY side effect — a no-op save must not broadcast, notify, or create history. All side effects run AFTER the commit, outside the transaction, so queue latency never holds the row lock. `lastUpdatedById` comes from `lastContext.user.id` (the auth context), not from an argument.
**Probe:** `grep -cF 'isDeepStrictEqual(tiptapJson, page.content)' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1), `grep -cF 'withLock: true' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1), `grep -cF 'document.broadcastStateless' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "onStoreDocument executeTx updatePage broadcastStateless", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-artifact dual-write (JSON for queries/render, binary CRDT state as source of truth, text for search) plus the deep-equal gate before side effects; adapt queue names and transclusion analogs; omit Nest/BullMQ specifics. Direct tests: none upstream for this extension; pinned by source read + probes.
