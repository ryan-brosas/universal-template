<!-- capsule-v2 -->
# JSON↔YDoc conversion ladder — how does legacy ProseMirror JSON become live CRDT state without corrupting existing docs?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** When is a Y.Doc hydrated from DB binary state vs converted from stored JSON, and how are whole-doc/append/prepend mutations applied safely?

## onLoadDocument fallback ladder + handler mutation modes
**Path/Symbol:** `apps/server/src/collaboration/extensions/persistence.extension.ts`:`onLoadDocument` (lines 52–96); `apps/server/src/collaboration/collaboration.handler.ts`:`updatePageContent` (lines 78–114); `apps/server/src/collaboration/collaboration.util.ts`:`prosemirrorNodeToYElement` (lines 217–244).
**Signature:** `onLoadDocument(data: onLoadDocumentPayload): Promise<Y.Doc | undefined>`; `prosemirrorNodeToYElement(node: any): Y.XmlElement | Y.XmlText`.
**Data Shape:** Everything lives in the `'default'` fragment; DB `page.ydoc` is a Uint8Array update, `page.content` is tiptap JSON.

### Decisive source
```ts
if (!document.isEmpty('default')) return;          // someone already populated it — never overwrite
const page = await this.pageRepo.findById(pageId, { includeContent: true, includeYdoc: true });
if (page.ydoc) { const doc = new Y.Doc(); Y.applyUpdate(doc, new Uint8Array(page.ydoc)); return doc; }
if (page.content) { return TiptapTransformer.toYdoc(page.content, 'default', tiptapExtensions); }
return new Y.Doc();
```
Mutation modes in the handler:
```ts
if (operation === 'replace') {
  if (fragment.length > 0) fragment.delete(0, fragment.length);
  const newDoc = TiptapTransformer.toYdoc(prosemirrorJson, 'default', tiptapExtensions);
  Y.applyUpdate(doc, Y.encodeStateAsUpdate(newDoc));     // replace = delete + apply foreign update
} else {
  const yElements = prosemirrorJson.content.map(prosemirrorNodeToYElement);
  fragment.insert(operation === 'prepend' ? 0 : fragment.length, yElements);  // append/prepend
}
```

**Flow:** load → empty? hydrate (binary first, JSON fallback, fresh doc last) → all server-side mutations run inside `withYdocConnection` (`openDirectConnection → transact → disconnect` finally).
**Invariant:** the `document.isEmpty('default')` guard is load-order-critical: returning a converted doc when the fragment already has content would resurrect stale JSON over newer CRDT state. Replace must DELETE the fragment range before applying — applying a full-state update alone merges rather than replaces.
**Probe:** `grep -cF "document.isEmpty('default')" apps/server/src/collaboration/extensions/persistence.extension.ts` (=1), `grep -cF 'TiptapTransformer.toYdoc(' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1), `grep -cF 'fragment.delete(0, fragment.length)' apps/server/src/collaboration/collaboration.handler.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "onLoadDocument isEmpty toYdoc applyUpdate default fragment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hydration precedence (live > binary > JSON > fresh) and the delete-then-apply replace semantics; adapt transformer/extension list; omit tiptap-specific extension wiring. No upstream direct test for these hooks; pinned by source read + probes.
