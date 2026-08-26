<!-- capsule-v2 -->
# Context-window synchronization — how do I stop host auto-compaction from firing before the remote harness compacts?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** The host compares `usage.totalTokens` against `model.contextWindow` to decide auto-compact, but the remote harness has its own (often larger, routing-adjusted) context budget and reports an exact meter — how do the two budgets stay consistent?

## Meter write-back + prompt-side-only totalTokens fallback
**Path/Symbol:** `src/providers.ts:applyContextStats` (1013-1037), totalTokens fallback inside `applyTurnUsage` (1083-1093).
**Signature:** `applyContextStats(output: AssistantMessage, model: Model<Api>, stats: { used?: unknown; limit?: unknown; [key: string]: unknown }): void`
**Data Shape:** Droid's `getContextStats()` returns `{ used?, remaining?, limit?, accuracy? }` for the ACTIVE model (already adjusted for reasoning effort / regional routing). Host consumes `output.usage.totalTokens` vs `model.contextWindow`.

### Decisive source
```ts
const limit = positiveNumberOrUndefined(stats.limit);
if (limit !== undefined) {
  // Droid's context meter reports the active model's effective max input,
  // including reasoning-effort and regional routing adjustments. Pi compares
  // usage.totalTokens against model.contextWindow for auto-compaction, so the
  // two values must describe the same budget. Mutating the active model here
  // prevents Pi's conservative catalog fallback (for example 128k for GLM)
  // from compacting before Droid's own context manager needs to.
  model.contextWindow = Math.round(limit);
}
const used = nonNegativeNumberOrUndefined(stats.used);
if (used !== undefined) {
  this.contextStatsUsed = used;
  // Keep input/output/cache as per-turn deltas for the footer counters while
  // reporting real window occupancy.
  output.usage.totalTokens = Math.round(used);
  output.usage.cost = calculateCost(model, output.usage);
}
```

Fallback when no exact meter exists — NEVER sum cumulative cache reads:
```ts
// Context occupancy for Pi: prefer exact meter, else prompt-side tokens only.
// Do not sum multi-million cumulative cache reads into totalTokens — that was
// blowing past contextWindow and forcing auto-compact every turn.
if (this.contextStatsUsed !== undefined) {
  output.usage.totalTokens = Math.round(this.contextStatsUsed);
} else {
  const promptTokens = output.usage.input + output.usage.cacheRead + output.usage.cacheWrite;
  const contextCap = model.contextWindow > 0 ? model.contextWindow : Number.POSITIVE_INFINITY;
  output.usage.totalTokens = Math.round(Math.min(promptTokens, contextCap));
}
```

**Flow:** finalize calls getContextStats → valid limit mutates the live model object (write-back) → valid used is memoized on the tracker AND stamped into the message → applyTurnUsage stamps occupancy as meter-used, else min(prompt-side sum, window).
**Invariant:** `usage.totalTokens` must describe the SAME budget as `model.contextWindow` at compact-decision time; per-bucket input/output/cache stay true per-turn deltas for display; invalid stats (`limit ≤ 0`, negative/NaN values) must be ignored without clobbering catalog metadata.
**Probe:** `test/usage.test.ts:77-93` ("caps totalTokens to contextWindow when no context stats" — deltas keep 790k/11.8M but totalTokens = 256k); `:95-108` ("prefers getContextStats used"); `:110-123` ("synchronizes Droid's effective context limit" — limit 908928 written onto a 128k model); `:125-133` ("ignores invalid limits without clobbering catalog metadata"). Runner caveat: suite blocked in this checkout (tsx absent); assertions read and pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "applyContextStats contextWindow totalTokens getContextStats", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt: write the remote meter's effective limit back onto the host model record, stamp exact `used` into totalTokens, clamp the no-meter fallback to min(prompt-side tokens, window), and validate stats with strict positive/non-negative guards. Adapt which field your host reads for compaction. Omit Droid's accuracy flag semantics.
