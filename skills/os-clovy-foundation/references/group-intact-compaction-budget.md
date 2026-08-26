<!-- capsule-v2 -->
# Group-intact compaction budget — when does history shrink and what is never split?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter implementing context-window management must decide the trigger threshold, what stays verbatim, and what happens when the summarizer model fails.

## compactHistory ladder
**Path/Symbol:** `agent-runtime/src/compaction.ts:compactHistory` (:17-91), `groupHistory` (:104-118), `summarizeOrFallback` (:120-139), `formatHistoryForSummary` (:141-151).
**Signature:** `compactHistory({history, contextWindow, maxOutputTokens?, summarize?, onFallback?, force?}): Promise<CompactionResult>`.
**Data Shape:** Items carry optional `estimatedTokens` (else `ceil(chars/4)` + 8 per item); groups are consecutive items sharing `groupId ?? callId ?? id`.

### Decisive source
```ts
const budget = Math.max(1_024, input.contextWindow - (input.maxOutputTokens ?? 4_096));
if (!input.force && estimatedTokens <= budget * 0.85) return { ...compacted: false };
// partition: real system instructions | prior context_summary items | conversation
const recent = groups.slice(-MIN_RECENT_GROUPS);            // 6
while (recent.length > 0 &&
       estimateHistoryTokens([...system, ...recent.flat()]) > budget * 0.75) {
  candidates.push(recent.shift());                          // oversized group NOT exempt
}
const summaryText = summaryResult.fallback
  ? formatHistoryForSummary(removed, maxSummaryChars)
  : unboundedSummary.length > maxSummaryChars ? slice + "\n[summary truncated]" : ...
const summary = { id:`context-summary-${Date.now()}`, kind:"context_summary",
                  role:"user", metadata:{ fallback } };
return { history:[...system, summary, ...recent.flat()], removedItemIds, ... };
```

**Flow:** estimate → 85% gate (or `force`) → partition → group → keep-last-6 with progressive fold at 75% → summarize-or-fallback (empty string counts as FAILURE; AbortError rethrown, never converted) → bounded summary item REPLACES all prior summaries in place between system head and recent tail.
**Invariant:** Tool call/result pairs are never separated (grouping by callId); system instructions never enter a summary; repeated compactions stay bounded because old summaries are folded INTO the new one, never accumulated; `removedItemIds` is exact so the host can mirror deletion; fallback summaries keep only the LAST maxChars (head truncated, marked `[earlier context truncated]`) and are labeled `metadata.fallback:true`.
**Probe:** `agent-runtime/test/compaction.test.ts` — "keeps system instructions, recent turns, and complete tool groups" (asserts no group split), "replaces prior context summaries instead of accumulating", "compacts an oversized recent group instead of exempting it", "falls back to deterministic context when model summarization times out". Executed live at pin (17/17).

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"history compaction token budget summary fallback groups", file_pattern:"agent-runtime/*" })
→ src.compaction.formatHistoryForSummary Function compaction.ts 141-151  (rank 1)
   src.compaction.compactHistory Function compaction.ts 17-91
   src.compaction.groupHistory Function compaction.ts 104-118
```

## Verdict
Adopt thresholds-as-fractions-of-budget (85% trigger / 75% retention), group-atomic eviction, and summary-replacement semantics; adopt the deterministic fallback so compaction never blocks a run on model health. Adapt token estimation and group keying to your history schema. Omit the Clovy prompt wrapper ("Earlier conversation context:") only if your consumer never pattern-matches it.
