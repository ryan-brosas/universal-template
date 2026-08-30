<!-- capsule-v2 -->
# Overflow recovery ladder — recovery must never depend on another LLM call

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** When the provider rejects a request for exceeding the context window, how does compaction guarantee the retry fits?

## Forced deterministic strategy with full custom-result acceptance bar
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction.ts:435-498` (overflow_recovery branch) + `:44-51` (`overflowRecovery` input contract).
**Signature:** `overflowRecovery?: boolean` on `ContextPipelinePrepareTurnInput`; effective mode becomes `"overflow_recovery"`, bypassing the estimate gate entirely.
**Data Shape:** Custom compactors get first shot but their result is validated: non-empty AND strictly smaller than input AND ≤ the recovery message target — all measured with the same token estimator.

### Decisive source
```ts
// The provider already rejected the request, so recovery must end
// deterministically: the agentic strategy's own summarizer call could
// overflow the same window ...
const acceptable =
    result.messages.length > 0 &&
    customMessageTokens < messageInputTokens &&
    customMessageTokens <= messageTargetTokens;
if (!acceptable) { ... result = undefined; }
...
if (!result?.messages) {
    executedStrategy = "basic";
    result = await BUILTIN_COMPACTION_STRATEGIES.basic(builtinOptions);
}
```

**Flow:** provider rejection → runtime sets `overflowRecovery:true` → gate skipped → custom compactor (if configured) tried once → acceptance bar enforced → ANY failure path (throw, decline/undefined, empty, non-shrinking, over-target) falls back to basic (deterministic) compaction. Cancellation (`AbortError`/`AgentRuntimeAbortError` while signal aborted) re-throws instead of falling back.
**Invariant:** Recovery never routes through another summarizer LLM request — the estimator that just undercounted is not trusted again; basic compaction's truncation math cannot overflow.
**Probe:** `grep -cF '=== "overflow_recovery"' sdk/packages/core/src/extensions/context/compaction.ts` → 3; `grep -cF 'customMessageTokens < messageInputTokens' ...` → 1; upstream test "forces a basic compaction on overflow recovery, bypassing the estimate gate" + five custom-compactor fallback tests pin every degenerate case.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "overflowRecovery compaction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-clause acceptance bar and the agentic→custom→basic ordering inversion during recovery; adapt the mode name/status notice strings to host vocabulary; omit telemetry event shapes. Upstream tests cover this plane exhaustively but were runner-blocked here (no node_modules); battery greps executed green.
