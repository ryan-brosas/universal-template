<!-- capsule-v2 -->
# Hybrid token estimation — how do you estimate context size when only some messages have provider usage?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter must decide "are we near the context window?" without a tokenizer — what counts as truth and what as guess?

## Provider usage is truth; char-heuristic only the trailing delta
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:216-244` (`estimateContextTokens`), helpers at `:164-213` (`calculateContextTokens`, `getAssistantUsage`, `getLastAssistantUsageInfo`), per-message estimator `estimateTokens` at `:270-311`.
**Signature:** `estimateContextTokens(messages: AgentMessage[]): { tokens; usageTokens; trailingTokens; lastUsageIndex: number | null }`.
**Data Shape:** Valid usage = assistant message whose stopReason ∉ {aborted, error} with `usage` whose total > 0. Scan BACKWARD for the last valid one; take its provider totals (`totalTokens || input+output+cacheRead+cacheWrite`); estimate ONLY messages after it.

### Decisive source
```ts
export function estimateContextTokens(messages: AgentMessage[]): ContextUsageEstimate {
	const usageInfo = getLastAssistantUsageInfo(messages);
	if (!usageInfo) {
		// no usage anywhere → pure estimation
		let estimated = 0;
		for (const message of messages) estimated += estimateTokens(message);
		return { tokens: estimated, usageTokens: 0, trailingTokens: estimated, lastUsageIndex: null };
	}
	const usageTokens = calculateContextTokens(usageInfo.usage);
	let trailingTokens = 0;
	for (let i = usageInfo.index + 1; i < messages.length; i++) trailingTokens += estimateTokens(messages[i]);
	return { tokens: usageTokens + trailingTokens, ... };
}
```

**Flow:** backward scan for last valid usage → anchor totals from the provider → `/4` chars-per-token heuristic over the trailing messages only (images count as flat `ESTIMATED_IMAGE_CHARS = 4800`; toolCall blocks count name + JSON-stringified args through `safeJsonStringify`, which returns `"[unserializable]"` instead of throwing). Threshold consumer: `shouldCompact = enabled && tokens > contextWindow - reserveTokens` (defaults reserve 16384 / keepRecent 20000).
**Invariant:** Never re-estimate what the provider already reported exactly; never let aborted/error/zero-usage messages anchor the estimate. The heuristic exists only to price the uncached tail.
**Probe:** `packages/agent/test/harness/compaction.test.ts:245` ("estimates tokens and context usage across supported message roles"), `:172` ("checks compaction threshold").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "estimateContextTokens getAssistantUsage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt usage-anchored-plus-tail estimation. Adapt ESTIMATED_IMAGE_CHARS and the /4 ratio to your tokenizer reality. Omit nothing. Coverage caveat: none.
