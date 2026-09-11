<!-- capsule-v2 -->
# Turn read/edit lifecycle — how does read-once-per-turn dedup stay correct when edits change the bytes?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you suppress repeated full-document reads within one assistant response WITHOUT freezing stale content after an edit?

## Identity-keyed read cache invalidated by edit + label repointing
**Path/Symbol:** `backend/src/lib/chat/tools/documentOps.ts:1375` (`getTurnReadIdentity`), `:1420` (`duplicateReadDocumentResult`), `:1438` (`clearTurnReadsForDocument`); consumers toolDispatcher.ts:478/:533 (inline veto), :1436/:1440-1453 (edit invalidation + repoint). Direct tests: `src/lib/__tests__/documentContext.test.ts` (dispatcher-level) + `src/lib/__tests__/documentGeneration.test.ts`.
**Signature:** `getTurnReadIdentity({docLabel, docStore, docIndex, db}) -> {key: "<documentId>:<versionId>", …} | null`; states live in streaming.ts:267-271 (`turnEditState`, `turnReadState` — Maps persist ACROSS tool-call batches within one assistant turn).
**Data Shape:** duplicate-read result is structured JSON `{ok:true, already_read:true, content:"…not repeated…", next_required_action:"use the prior result / find_in_document / edit_document"}`.

### Decisive source
```ts
const reuseVersion = turnEditState?.get(indexed.document_id);
const result = await runEditDocument({ …, reuseVersion });   // 2nd edit in one turn OVERWRITES the turn's version
if (result.ok) {
    turnEditState?.set(indexed.document_id, { versionId: result.version_id, … });
    clearTurnReadsForDocument(turnReadState, indexed.document_id);   // post-edit re-read becomes legal
    if (docIndex[docId]) docIndex[docId] = { …docIndex[docId],
        version_id: result.version_id, version_number: result.version_number }; // label → NEW bytes
```

**Flow:** read_document resolves identity FIRST (`documentId:activeVersionId` via DB, falling back to `label:storage_path` for request-scoped/inline docs) → cache hit returns the token-saving stub instead of re-extracting text → edit_document reuses the turn's existing version row (one versions row per doc per TURN, not per call) → clears that document's read entries and repoints BOTH maps so subsequent reads/cites hit the edited bytes.
**Invariant:** The guard key is CONTENT IDENTITY (document+version), never the label or filename — a re-read after an edit MUST pass because the version changed. Request-scoped inline documents (Word add-in body posted with the request) enter model context ONLY through read/fetch paths; find_in_document on them is vetoed (:533-545) because raw snippets would bypass the nonce fence and visible read lifecycle.
**Probe:** `grep -n 'already_read' src/lib/chat/tools/documentOps.ts` → :1427 single site; `grep -c 'must be opened with read_document' src/lib/__tests__/documentContext.test.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "getTurnReadIdentity clearTurnReadsForDocument duplicateReadDocumentResult", limit: 10 });
```

## Verdict
Adopt identity-keyed read dedup + edit-invalidates-reads + version-row reuse per turn as portable contracts; adapt stub copy and inline-doc handling to your client.
