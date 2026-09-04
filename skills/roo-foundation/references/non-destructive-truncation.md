<!-- capsule-v2 -->
# Non-destructive sliding window — how do you hide half the history yet still let rewind restore it?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Truncation used to delete messages irreversibly — what tagging scheme hides messages from the API while keeping them restorable?

## truncateConversation: tag-don't-delete with an even-pair rule and boundary marker
**Path/Symbol:** `src/core/context-management/index.ts:65-131` (`truncateConversation`); marker type fields in `src/core/task-persistence/apiMessages.ts:31-37`.
**Signature:** `truncateConversation(messages: ApiMessage[], fracToRemove: number, taskId: string): TruncationResult { messages, truncationId, messagesRemoved }`.
**Data Shape:** Hidden messages gain `truncationParent = truncationId`; ONE synthetic user marker `{ isTruncationMarker: true, truncationId, ts: firstKeptTs - 1 }` records the boundary; already-tagged/hidden messages are invisible to future rounds.

### Decisive source
```ts
const visibleIndices = /* indices where !msg.truncationParent && !msg.isTruncationMarker */
const raw = Math.floor((visibleCount - 1) * fracToRemove)
const messagesToRemove = raw - (raw % 2)        // EVEN: assistant+user pairs never split
const indicesToTruncate = new Set(visibleIndices.slice(1, messagesToRemove + 1)) // skip first visible
// marker ts = firstKeptTs - 1 keeps it ordered BEFORE the first kept message
const truncationMarker = { role: "user",
  content: `[Sliding window truncation: ${messagesToRemove} messages hidden...]`,
  ts: firstKeptTs - 1, isTruncationMarker: true, truncationId }
```

**Flow:** collect visible indices (skip previously hidden/marker rows) → size the cut as an even count of visible messages after the first → tag those with truncationParent (spread-copy, original objects untouched) → insert the marker just before the first kept message. Because nothing is deleted, `getEffectiveApiHistory` drops hidden rows only while their marker exists, and MessageManager rewinds remove the marker to resurrect everything.
**Invariant:** The first message is NEVER hidden; pairs are kept whole (even rounding) so tool_use/tool_result adjacency survives; repeated truncations compose because each round only sees currently-visible rows.
**Probe:** `src/core/context-management/__tests__/truncation.spec.ts` ("should tag messages with truncationParent instead of deleting" :27, marker insert :53, even rounding :75, multi-truncation rewind :268).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "truncateConversation truncationParent marker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tag-based hiding with even-pair rounding + boundary markers; pair it with existence-keyed filtering (effective-api-history capsule) — neither works alone. Adapt marker text/format. Nothing roo-specific worth omitting.
