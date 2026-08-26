<!-- capsule-v2 -->
# Cumulative usage baseline — how do I convert session-cumulative token counters into truthful per-turn usage?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** The remote harness reports SESSION-CUMULATIVE token counters (and a last-call notification), but the host treats each assistant message's usage as one request — what arithmetic keeps per-turn numbers honest across many turns?

## Baseline subtraction with snapshot-first finalize
**Path/Symbol:** `src/providers.ts:UsageTracker` (944-1113), `readTokenBuckets` (1115-1134).
**Signature:** `cumulativeToTurnBuckets(usage: { inputTokens?, outputTokens?, thinkingTokens?, cacheReadTokens?, cacheCreationTokens? }): TokenBuckets`; `applyTurnUsage(output, turn: TokenBuckets, model, opts: { preferLastCall: boolean }): void`; `finalize(droidSession, output, model): Promise<void>`.
**Data Shape:** `TokenBuckets = { input, output, cacheRead, cacheWrite }`; tracker keeps private `baseline`, `latestCumulative`, `lastCallUsage`, `contextStatsUsed` per Droid session; notifications (`session_token_usage_changed`) carry `lastCallTokenUsage` and cumulative `tokenUsage ?? inclusiveTokenUsage`.

### Decisive source
```ts
const cumulative: TokenBuckets = {
  input: usage.inputTokens ?? 0,
  output: (usage.outputTokens ?? 0) + (usage.thinkingTokens ?? 0),
  cacheRead: usage.cacheReadTokens ?? 0,
  cacheWrite: usage.cacheCreationTokens ?? 0,
};
this.latestCumulative = cumulative;
return {
  input:   Math.max(0, cumulative.input   - this.baseline.input),
  output:  Math.max(0, cumulative.output  - this.baseline.output),
  cacheRead: Math.max(0, cumulative.cacheRead - this.baseline.cacheRead),
  cacheWrite: Math.max(0, cumulative.cacheWrite - this.baseline.cacheWrite),
};
```

Finalize advances the baseline — from the authoritative cumulative snapshot when available, else by accumulating the reported deltas:
```ts
if (this.lastCallUsage) {
  this.applyTurnUsage(output, this.lastCallUsage, model, { preferLastCall: true });
}
...
if (this.latestCumulative) {
  this.baseline = { ...this.latestCumulative };
} else {
  this.baseline = {
    input: this.baseline.input + Math.max(0, output.usage.input), /* ...per bucket */
  };
}
```

preferLastCall merge rule:
```ts
// lastCall is authoritative for prompt/cache size when present; keep the
// larger output delta if stream cumulative saw more generation tokens.
output.usage.output = Math.max(output.usage.output, turn.output);
```

**Flow:** beginTurn clears lastCall/latestCumulative/contextStats and re-attaches the notification listener → each mid-stream TokenUsageUpdate/Result maps fields (thinking folds into OUTPUT) and subtracts baseline → finalize prefers lastCall buckets for prompt/cache while keeping max(output), then advances baseline.
**Invariant:** Per-turn numbers must never go negative (clamp at 0) and must reset every turn even though the source counter only grows; baseline advancement must be idempotent per turn — snapshot copy when available, else add-the-deltas, so drift cannot compound silently. `beginTurn` MUST clear stale last-call/cumulative state or turn N+1 reports turn N.
**Probe:** `test/usage.test.ts:60-75` ("cumulativeToTurnBuckets subtracts session baseline" — 130k−100k=30k etc., thinking folded into output); `:135-148` ("preferLastCall keeps larger streamed output delta"); `:150-165` ("readTokenBuckets maps Droid notification fields", null/{} → null); `:167-192` ("baseline advances from cumulative snapshot"). Runner caveat: suite blocked in this checkout (tsx absent); assertions read and pinned line-by-line.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "UsageTracker cumulativeToTurnBuckets applyTurnUsage advanceBaselineFromCumulative", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the whole meter as a portable unit: bucket struct with thinking→output folding, clamped baseline subtraction, notification-fed lastCall/cumulative capture, snapshot-first baseline advance, and the preferLastCall max-output merge. Adapt field names to your remote's usage payload. Omit the Pi-specific footer/auto-compact consumers of these numbers.
