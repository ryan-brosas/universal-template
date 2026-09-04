<!-- capsule-v2 -->
# Stream citations gate — how do you hide the CITATIONS block from visible deltas while still streaming it to the parser?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you split a token stream at a marker that may arrive split across deltas, without emitting a partial tag to the UI or losing characters?

## Hold-back tail buffer of marker-length−1 chars
**Path/Symbol:** `backend/src/lib/chat/streaming.ts:311` (`streamVisibleContent`), `:350` (`flushVisibleTail`), `:294` (`streamHiddenCitationContent`). Direct test: integration coverage via `src/__tests__/integration/chat.routes.test.ts` + partial parser tests `src/lib/__tests__/citations.test.ts`.
**Signature:** closure state: `visibleTailBuffer`, `citationsOpenSeen`, `streamingCitationsBuffer`, `streamedCitationCount`.
**Data Shape:** visible deltas are `{type:"content_delta", text}` SSE events; once `<CITATIONS>` is seen, subsequent text routes ONLY into the partial-citation parser (`status:"partial"/"started"` snapshot events instead).

### Decisive source
```ts
const combined = visibleTailBuffer + delta;
const markerIdx = combined.indexOf(CITATIONS_OPEN_TAG);
if (markerIdx >= 0) { /* emit pre-marker, flip gate, feed the REST hidden */ }
// hold back the last (TAG.length - 1) chars: any prefix of the marker that
// could still be completed by the NEXT delta must not reach the client
const keep = Math.min(CITATIONS_OPEN_TAG.length - 1, combined.length);
visibleTailBuffer = combined.slice(combined.length - keep);
```

**Flow:** accumulate → search combined for the open tag → found: emit everything before it as content, emit `{type:"citations",status:"started"}`, switch gate, feed remainder+future deltas to `parsePartialCitationObjects` → not found: emit all but the tail buffer, keep tail. On iteration/turn end `flushVisibleTail` drains the buffer unless the gate flipped.
**Invariant:** No character is ever emitted twice or dropped: the tail is re-scanned on every delta and flushed exactly once. State resets per ITERATION in `flushText` (multi-tool-turn responses re-arm the gate). The hidden branch NEVER emits content_delta — the block stays invisible even though the model streamed it.
**Probe:** `grep -n "visibleTailBuffer" src/lib/chat/streaming.ts | head -5` pins the mechanism; behavioral proof rides the partial-citation suite (7 cases) + chat route integration test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "runLLMStream sanitizeAssistantEvent error streaming content_delta citations", limit: 10 });
```

## Verdict
Adopt tail-hold-back splitting + one-way visibility gate + per-iteration reset; adapt the marker constant to your protocol; omit SSE event naming.
