<!-- capsule-v2 -->
# Doc context sweeps — which documents exist for this chat, including ones never attached to a user message?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How does the per-turn document index (docIndex/docStore) get built so generated/edited/replicated docs stay reachable in LATER turns?

## Attachments ∪ prior-event UUID sweep, ready-only, stable doc-N slugs
**Path/Symbol:** `backend/src/lib/chat/contextBuilders.ts:554` (`buildDocContext`), `:661` (`buildProjectDocContext`). Direct test: `src/lib/__tests__/documentContext.test.ts` (16 cases).
**Signature:** `buildDocContext(messages, userId, db, chatId?) -> { docIndex, docStore }`.
**Data Shape:** `docIndex: Record<"doc-N", {document_id, filename, version_id?, version_number?}>`; `docStore: Map<doc-N, {storage_path, file_type, filename, source_kind?}>` — two parallel maps because citations need identity+version while tools need bytes+type.

### Decisive source
```ts
// Also pull document_ids from prior assistant events — generated docs and
// tracked-change edits aren't attached to user messages as files… Without this
// sweep the model loses access to generated docs after the turn that created
// them.
if (ev?.type === "doc_created" || ev?.type === "doc_edited") …
else if (ev?.type === "doc_replicated") for (const copy of ev.copies) …
// then: .in("id", ids).eq("user_id", userId).eq("status", "ready")
```

**Flow:** collect UUIDs from message files + sweep ALL prior assistant rows for doc_created/doc_edited/doc_replicated.copies → single `in`-query filtered by owner AND status="ready" → `attachActiveVersionPaths` fills storage paths from the ACTIVE version → assign labels `doc-{i}` by ARRAY POSITION (stable within a turn; the system prompt lists them; model cites them). Project variant additionally resolves folder paths (`parent_folder_id` walk → "A / B / C" strings).
**Invariant:** Docs without a storage path are skipped silently (never crash the turn); ownership re-checked here regardless of how the UUID was obtained; library templates carry `source_kind:"library_template"` so downstream immutability gates can fire. Labels are positional — adding docs mid-turn appends via lowest-free-index scan (`doc-${i}` while-exists loop), never renames existing ones.
**Probe:** `cd backend && bunx vitest run src/lib/__tests__/documentContext.test.ts` (`bunx vitest run` → **16 passed** at pin; plain `grep -c 'it('` overcounts at 17 by matching `split(`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "enrichWithPriorEvents buildDocContext docIndex docStore", limit: 10 });
```

## Verdict
Adopt dual-map context shape + history-sweep for tool-created documents + owner/status re-filter; adapt label scheme (any stable per-turn handle works) and folder-path resolution to your schema.
