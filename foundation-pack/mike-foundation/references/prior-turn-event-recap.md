<!-- capsule-v2 -->
# Prior-turn event recap — how does the model learn what its last turn produced without re-reading raw events?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you give the LLM a compact "tool activity in your previous turn" summary while keeping every user-controlled string in it fenced?

## Last-assistant-events → bullet lines, filenames spotlight-fenced
**Path/Symbol:** `backend/src/lib/chat/contextBuilders.ts:144` (`enrichWithPriorEvents`). Direct test: `src/lib/__tests__/spotlight.test.ts:74` ("fences document names and workflow titles replayed from prior events").
**Signature:** `enrichWithPriorEvents(messages, chatId, db, docIndex, nonce?, messageTable?) -> ChatMessage[]`.
**Data Shape:** reads the newest assistant row with content IS NOT NULL (array of typed events), maps event types to lines: `generated_document`/`edit_document`/`read_document`/`replicate_document (copy of …)`/`applied workflow`/`asked user for N inputs`/user answers & attachments.

### Decisive source
```ts
// Skip streaming reservations: routeStreaming inserts the assistant row with
// content = null BEFORE the stream runs, so a crashed stream (or a concurrently
// streaming POST) leaves a newer null-content row that would otherwise shadow
// the previous turn's real events here.
.not("content", "is", null).order("created_at", { ascending: false }).limit(1)
```

**Flow:** build `document_id → doc-N slug` map so lines hand back the SAME handle the model uses for read/edit calls (`doc-3 (filename)` with filename fenced) → append `[Tool activity in your previous turn]\n…` to the LAST assistant message only (reverse scan for role==="assistant") → no-op when zero lines or no assistant message.
**Invariant:** Every filename/title/answer passing into the recap goes through `untrustedRef` (= spotlight when nonce present) because prior-event strings are user-controlled replay surface. Reservation rows must be skipped or a crashed stream's null row erases the recap.
**Probe:** `grep -c 'it(' src/lib/__tests__/spotlight.test.ts | head -1`; targeted: `grep -c "fences document names and workflow titles replayed from prior events" src/lib/__tests__/spotlight.test.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "enrichWithPriorEvents buildDocContext docIndex docStore", limit: 10 });
```

## Verdict
Adopt event-recap injection onto the last assistant turn + reservation-row skip + full fencing of replay strings; adapt event-type vocabulary and line copy.
