<!-- capsule-v2 -->
# Summary request isolation — how do you call the LLM for a summary without polluting routing, cache, or budget?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter's summary completions corrupt prompt-cache stats and get billed against the session's token budget — what does pi do differently?

## Standalone requests: no cache writes, fresh session id, capped output
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:102-122` (`completeSimpleWithRetries`), budgets at `:541-544` (history) and `:805-808` (turn-prefix); branch twin `branch-summarization.ts:249-256` (`{ signal, maxTokens: 2048 }`).
**Signature:** `completeSimpleWithRetries(models, model, context, options, retry?, callbacks?): Promise<AssistantMessage>` — wraps `models.completeSimple` in `retryAssistantCall`.
**Data Shape:** Request options are overridden, not merged from caller: `cacheRetention: "none"` and `sessionId: uuidv7()` on EVERY summary call.

### Decisive source
```ts
// Summaries are standalone requests, so isolate routing and avoid cache
// writes that cannot be reused.
const requestOptions: SimpleStreamOptions = {
	...options,
	cacheRetention: "none",
	sessionId: uuidv7(),
};
return retryAssistantCall(() => models.completeSimple(model, context, requestOptions), retry, requestOptions.signal, callbacks);
```

**Flow:** every summarization path (compaction history summary, turn-prefix summary, branch summary) funnels through this one wrapper → provider sees a brand-new session with caching disabled → retries re-run through the same isolated options. Output caps: history summary `maxTokens = min(floor(0.8 × reserveTokens), model.maxTokens if > 0)`; turn-prefix uses 0.5 × reserveTokens; branch summaries fixed at 2048.
**Invariant:** A summary is not part of the conversation's request lineage — it must never write prompt-cache entries that can't be reused, never share the session's routing id, and never exceed its slice of the reserve. Aborted/error stop reasons become typed `CompactionError`/`BranchSummaryError` results ("aborted" / "summarization_failed"), never thrown.
**Probe:** `packages/agent/test/harness/compaction.test.ts:547/:579/:598` ("clamps compaction summary maxTokens to the model output cap" / "returns compaction error results without throwing" / "combines usage for split-turn compaction summaries").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "completeSimpleWithRetries cacheRetention", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-summary isolation (no-cache + fresh session) and reserve-sliced maxTokens. Adapt cap ratios to your window math. Omit the split-turn usage-combining helper unless you port split turns. Coverage caveat: none.
