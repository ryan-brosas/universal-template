<!-- capsule-v2 -->
# Optimistic user message queue — clearing the right "Sending…" bubble by server echo, and never hanging forever

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How does an optimistic send bubble get consumed by exactly its own server echo across parallel conversations/sub-agents, and fail visibly when the echo never comes?

## Connected graph-selected seam
**Path/Symbol:** `src/stores/optimistic-user-message-store.ts:consumeMatchingPendingMessage` (169–198), `enqueuePendingMessage` (115–142), `reassignPendingMessages` (202–209); call site `conversation-websocket-context.tsx:handleMainMessage`.
**Signature:** `consumeMatchingPendingMessage(conversationId: string, content: string): PendingUserMessage | null`.
**Data Shape:** Pending entry: `{ id, conversationId, text /* bubble */, content /* exact bytes sent */, status: "sending"|"error", imageUrls, fileUrls, timestamp, errorMessage? }`. Bubble text and sent content are deliberately separate fields (attachments append "Files uploaded: …" to what is sent).

### Decisive source
```ts
// We prefer an exact content match (this is what makes out-of-order echoes safe:
// an echo of "world" will pop the "world" bubble, not the older "hello" one).
// If no exact match exists — e.g. the server slightly munged the body — fall back
// to the oldest "sending" entry in this conversation so the user doesn't end up
// with a permanently-stuck bubble in the happy-path single-message case.
let consumed: PendingUserMessage | null = null;
set((state) => {                       // single atomic set: find + filter can't interleave
  const sending = state.pendingMessages
    .map((m, i) => ({ m, i }))
    .filter(({ m }) => m.status === "sending" && m.conversationId === conversationId)
    …                                    // exact-content match first, FIFO fallback
});
```
Watchdog (`enqueuePendingMessage`): a `PENDING_MESSAGE_TIMEOUT_MS = 150_000` timer flips still-"sending" entries to `status:"error"` ("Send timed out") so a dropped socket yields a retry link instead of a pinned bubble. The echoed user message reaches the handler as a normal `MessageEvent`; `extractMessageEventText` concatenates its TextContent parts to rebuild the exact sent prompt.

**Flow:** send succeeds → enqueue bubble ("sending") + start 150s watchdog → server echoes the user message over WS (or it arrives in a REST history preload — both paths consume) → handler scopes to the MAIN conversationId (planning sub-agent echoes may never pop main bubbles) → exact-content match pops that bubble; munged bodies fall back to FIFO → draft cleared from localStorage; timeout path flips to error+retry instead.

**Invariant:** Matching is scoped by conversationId; consumption happens in ONE atomic set; every pending entry either resolves by echo or transitions to visible error within 150s; provisioning can reassign entries from `task-{uuid}` provisional ids to the real conversation id.

**Probe:** `__tests__/stores/optimistic-user-message-store.test.ts` pins matching/fallback/timeout semantics. RUNNER BLOCK: vitest not executable here; decisive ranges read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "optimistic pending user message consume matching echo timeout", limit: 8 });
// executed this pass -> consumeMatchingPendingMessage src/stores/optimistic-user-message-store.ts 169-198,
// enqueuePendingMessage 115-142, reassignPendingMessages 202-209
```

## Verdict
Adopt exact-content-first/FIFO-fallback echo matching, conversation scoping, the timeout watchdog, and the split bubble-text vs sent-content fields. Adapt timeouts and transport to your host. Omit OpenHands task-provisioning reassignment specifics beyond the pattern. Coverage: `no_recorded_issue` on source and test paths.
