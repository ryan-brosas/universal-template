<!-- capsule-v2 -->
# Split-turn compaction — how do you compact when the token budget lands inside a turn?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** The keep-recent budget falls mid-turn — what gets summarized, what is kept, and what does the model see?

## Two summaries, joined with a labeled seam
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:707-794` (`compact`), prefix generator `:795-848` (`generateTurnPrefixSummary`), prefix prompt `:689-702`; preparation side `:652-675` (historyEnd / turnPrefixMessages / retainedTail slicing).
**Signature:** `compact(preparation, models, model, …): Promise<Result<CompactResult, CompactionError>>`.
**Data Shape:** When `isSplitTurn && turnPrefixMessages.length > 0`: history range [0, turnStartIndex) → standard summary; prefix range [turnStartIndex, firstKeptEntryIndex) → separate "Original Request / Early Progress / Context for Suffix" summary; retained tail = [firstKeptEntryIndex, end).

### Decisive source
```ts
if (isSplitTurn && turnPrefixMessages.length > 0) {
	let historyText = "No prior history.";
	let historyUsage: Usage | undefined;
	if (messagesToSummarize.length > 0) { /* generateSummaryWithUsage → historyText/usage */ }
	const turnPrefixResult = await generateTurnPrefixSummary(turnPrefixMessages, models, model, settings.reserveTokens, ...);
	if (!turnPrefixResult.ok) return err(turnPrefixResult.error);
	summary = `${historyText}\n\n---\n\n**Turn Context (split turn):**\n\n${turnPrefixResult.value.text}`;
	summaryUsage = historyUsage ? combineUsage(historyUsage, turnPrefixResult.value.usage) : turnPrefixResult.value.usage;
}
```

**Flow:** cut point says split → summarize full history (feeding previousSummary if present) → separately summarize ONLY the abandoned turn prefix with a prompt that names it as "the PREFIX of a turn … The SUFFIX (recent work) is retained" and asks for context needed to understand the kept suffix → join with the `\n\n---\n\n**Turn Context (split turn):**\n\n` marker → append deterministic file-op tags. Prefix maxTokens = 0.5 × reserveTokens. Either request failing fails the whole compaction as a typed error.
**Invariant:** The retained tail must still BEGIN at a turn boundary even though an earlier part of that same turn was dropped — the split is legal only because the prefix is summarized separately and explicitly labeled, so the model never sees an unexplained half-conversation.
**Probe:** `packages/agent/test/harness/compaction.test.ts:407/:598/:622/:647` ("prepares split-turn compaction with prior file-operation details" / "combines usage for split-turn compaction summaries" / reasoning pass-through / error results).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "generateTurnPrefixSummary splitTurn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-request split handling with the labeled join and usage combining. Adapt the marker text to your UI. Omit entirely if your keep-recent budget can never land mid-turn (then enforce cut-at-turn-boundary only). Coverage caveat: none.
