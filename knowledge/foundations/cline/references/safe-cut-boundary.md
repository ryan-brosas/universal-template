<!-- capsule-v2 -->
# Safe cut boundary — never orphan half a tool_use/tool_result pair

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** Where may an agentic compaction place the summary/tail cut so providers still accept the transcript?

## Assistant messages ARE safe cuts; tool-result-only user messages are NOT
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction-shared.ts:317-364` (`isSafeCutBoundary`, `findCutIndex`).
**Signature:** `findCutIndex(messages, preserveRecentTokens, estimateMessageTokens): number`.
**Data Shape:** Walks backward accumulating per-message token estimates until `preserveRecentTokens` is covered (candidate = oldest kept index), then clamps and snaps.

### Decisive source
```ts
// A tool_result-only user message is never safe — its matching tool_use sits
// in the preceding assistant message and would be folded into the summary,
// leaving an orphaned tool_result the provider rejects.
function isSafeCutBoundary(message: MessageWithMetadata): boolean {
    return message.role === "assistant" || isTurnStartMessage(message);
}
...
const lastTurnStartIndex = findLastTurnStartIndex(messages);
let cut =
    lastTurnStartIndex > 0
        ? Math.min(candidate, lastTurnStartIndex)
        : candidate;
while (cut > 0 && !isSafeCutBoundary(messages[cut])) { cut -= 1; }
```

**Flow:** backward token walk → candidate → clamp to at-or-before the latest typed user prompt when one exists past index 0 (whole latest turn survives verbatim; transcripts without a later typed turn — one task + long tool loop, or a projection starting with a compaction summary — still cut at the budget candidate) → snap down to the nearest safe boundary.
**Invariant:** Because an assistant's tool_use keeps its results in the FOLLOWING user message, cutting before an assistant message can never split a pair; cutting before a tool_result-only user message always does. `findTurnStart` excludes both tool-result-only users AND prior compaction summaries (metadata.kind==="compaction_summary").
**Probe:** `grep -cF 'message.role === "assistant" || isTurnStartMessage(message)' .../compaction-shared.ts` → 1; upstream tests "never lands the agentic cut in the middle of a tool pair" + "compacts a single-task tool loop by cutting at an assistant boundary" pin it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "findCutIndex safe boundary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the role-based boundary rule verbatim — it is the cheapest correct provider-compatibility guard; adapt the preserve-recent default (20k tokens) to host policy; omit Cline's userRunSpan bookkeeping on summaries if unused. Runner blocked (no node_modules); battery greps executed green.
