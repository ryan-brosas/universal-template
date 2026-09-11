<!-- capsule-v2 -->
# Fresh-start condensation — how do you summarize a whole conversation into ONE user message without losing undo or active workflows?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does roo condense so the model sees only a summary while storage keeps everything rewritable?

## summarizeConversation: fresh-start model with tagged parents
**Path/Symbol:** `src/core/condense/index.ts:254-503` (`summarizeConversation`); thresholds `MIN_CONDENSE_THRESHOLD=5` / `MAX_CONDENSE_THRESHOLD=100` (:109-110); helpers `getMessagesSinceLastSummary` :512-521, `cleanupAfterTruncation` :646-694.
**Signature:** `summarizeConversation(options): Promise<SummarizeResponse>` with `{ messages, summary, cost, newContextTokens?, error?, errorDetails?, condenseId? }`.
**Data Shape:** Summary message: `role:"user"` (fresh-start!), `ts: lastMsgTs + 1`, `isSummary:true`, `condenseId:<uuid>`. EVERY prior message gets `condenseParent = condenseId` unless it already has one.

### Decisive source
```ts
// NON-DESTRUCTIVE CONDENSE: storage after =
// [msg1(parent=X) ... msgN(parent=X), summary(id=X)]
// Effective for API (filtered by getEffectiveApiHistory): [summary]  ← fresh start
const newMessages = messages.map((msg) => {
  // nested condense handled by filtering, not re-tagging
  if (!msg.condenseParent) return { ...msg, condenseParent: condenseId }
  return msg
})
newMessages.push(summaryMessage)
```
Pre-send transforms: `injectSyntheticToolResults` appends placeholder results for orphan `tool_use` ids (OpenAI Responses API rejects orphans when condense fires mid-tool); `transformMessagesForCondensing` converts every tool_use/tool_result block to TEXT so summarization needs no `tools` param (Bedrock/LiteLLM requirement).

**Flow:** guards (≤1 message since last summary → error "condensed_recently"; recent summary present → refuse) → build request messages (synthetic results + text-ified blocks + final user instruction = custom prompt or `supportPrompt.default.CONDENSE`) → stream summary via `SUMMARY_PROMPT` system text that forbids tool use and excludes itself from "user intent" analysis → assemble summary content blocks: `## Conversation Summary` + `<system-reminder>Active Workflows</system-reminder>` (command blocks re-extracted FROM THE ORIGINAL FIRST MESSAGE so workflows survive repeated condenses) + per-file folded signatures + environmentDetails ONLY when `isAutomaticTrigger` (manual triggers get fresh details next turn anyway) → count real next-context tokens (summary content + system prompt + JSON-stringified tools), not outputTokens.
**Invariant:** Summaries are USER-role messages; merging/shaping must never merge a summary INTO another message (see api-shaping capsule). Error path returns typed `{error, errorDetails}` (HTTP status/code/body serialized) instead of throwing — callers decide UI.
**Probe:** `src/core/condense/__tests__/condense.spec.ts` (`summarizeConversation` :120+, `getEffectiveApiHistory` :334+, command-block preservation :61+); `nested-condense.spec.ts`; `rewind-after-condense.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "summarizeConversation condenseParent fresh start", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parent-tagged fresh-start condensation with workflow/command re-injection and synthetic tool-result patching. Adapt the summary prompt text and threshold bounds. Omit i18n error strings and provider-specific image stripping internals.
