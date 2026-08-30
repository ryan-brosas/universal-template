<!-- capsule-v2 -->
# Agentic summarizer budget — the summarizer call itself must not overflow

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How is the conversation-to-summarize sized against the SUMMARIZER model's window, and when does compaction skip instead of summarize?

## Input-budget projection before serialization; incremental fold past prior summary
**Path/Symbol:** `sdk/packages/core/src/extensions/context/agentic-compaction.ts:116-257` (`runAgenticCompaction`) + `:49-60` (`buildAgenticSummaryInputBudget`).
**Signature:** `runAgenticCompaction({context, providerConfig, summarizer?, preserveRecentTokens, estimateMessageTokens, logger?}) → CoreCompactionResult | undefined`.
**Data Shape:** `MIN_AGENTIC_SUMMARY_INPUT_TOKENS = 1_024` floor; limit ladder = summarizer's own resolved input limit → (no explicit summarizer) active-context limit `max(maxInputTokens, triggerTokens, 1024)` → (explicit summarizer with unknown limit) 1024 + warn. `availableSummaryInputTokens = summarizerInputLimit - estimateTokens(buildSummaryRequest(...,"" conversation).length)`.

### Decisive source
```ts
const canUseActiveContextLimit = options.summarizer === undefined;
...
if (availableSummaryInputTokens <= 0) { ... return undefined; }
const summaryInputBudget = buildAgenticSummaryInputBudget({
    messages: newMessagesToFold,
    targetTokens: availableSummaryInputTokens,
    estimateMessageTokens: options.estimateMessageTokens,
});
if (summaryInputBudget.status === "failed") { ... return undefined; }
const fileOps = extractFileOps(summaryInputBudget.messages);   // AFTER projection
const conversationText = serializeConversation(summaryInputBudget.messages);
```

**Flow:** cut via findCutIndex → locate latest PRIOR summary inside the dropped span → fold only `slice(latestSummaryIndex+1)` (incremental summaries chain via "Previous summary:" in the request template) → project the fold-set under the summarizer budget (drops/truncates per budget-projection policies) → serialize projected set → stream summary (reasoning chunks counted but discarded) → empty text ⇒ skip with diagnosis (`output_budget_consumed_by_reasoning` vs `empty_response`) → result = [summary message] + untouched tail.
**Invariant:** Budgeting happens on token-estimated MESSAGES and only then serializes; file-ops for the Files section are re-extracted from the PROJECTED messages so the summary never references dropped content. A summarizer that produced only thinking output yields NO summary text ⇒ compaction skipped (never a fabricated summary).
**Probe:** `grep -cF 'MIN_AGENTIC_SUMMARY_INPUT_TOKENS = 1_024' .../agentic-compaction.ts` → 1; `grep -cF 'options.summarizer === undefined' ...` → 1; upstream tests "budgets agentic summary input before serialization", "skips with a diagnostic warning when the summarizer only produced reasoning output".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "runAgenticCompaction summarizer budget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt estimate→project→serialize ordering, the three-rung summarizer-limit ladder, and the incremental prior-summary fold; adapt the summary prompt template (Goal/State/Highlights/Next/Files) to host needs; omit Cline's openai-codex special-case (strip maxOutputTokens, force thinking:false) unless porting that provider. Runner blocked honestly; battery greps green.
