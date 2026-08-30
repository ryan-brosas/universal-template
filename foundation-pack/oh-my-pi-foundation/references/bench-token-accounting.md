<!-- capsule-v2 -->
# Cross-provider token accounting — comparable input-token metrics over different cache behaviors

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you measure per-attempt token cost so numbers are comparable across providers whose caching reports the same prompt in different buckets — and exclude constant boilerplate from the metric?

## Four-bucket prompt sum + per-call system-overhead subtraction
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts`:`diffTokenStats` (1771-1791), `estimateTokens` (1767-1769), session stats via `client.getSessionStats()` (`SessionTokenStats`, 1793-1796).
**Signature:** `function diffTokenStats(before: SessionTokenStats, after: SessionTokenStats, systemPromptTokens: number): TokenStats`; `estimateTokens(text): number` = `ceil(len/4)`.
**Data Shape:** provider session stats expose `{tokens: {input, output, reasoning, cacheRead, cacheWrite}, assistantMessages}`; result `TokenStats = {input, output, reasoning, total}` where `total = input + output`.

### Decisive source
```ts
// `input` here is the total prompt tokens delivered to the model on the wire,
// summed across all four buckets the providers expose: non-cached input,
// cacheRead, cacheWrite. Summing makes the metric comparable across providers
// with different caching behavior — Anthropic with a hot cache reports its
// prompt entirely under cacheRead/cacheWrite while non-caching providers put
// the same content under `input`.
//
// The system prompt and tool definitions are constant per-call overhead. We
// subtract `calls * systemPromptTokens` once per assistant turn so the
// reported figure reflects task-driven prompt cost rather than fixed boilerplate.
const calls = Math.max(0, after.assistantMessages - before.assistantMessages);
const overhead = calls * systemPromptTokens;
const beforePrompt = before.tokens.input + before.tokens.cacheRead + before.tokens.cacheWrite;
const afterPrompt  = after.tokens.input + after.tokens.cacheRead + after.tokens.cacheWrite;
const input   = Math.max(0, afterPrompt - beforePrompt - overhead);
const output  = Math.max(0, after.tokens.output - before.tokens.output);
const reasoning = Math.max(0, after.tokens.reasoning - before.tokens.reasoning);
```

**Flow:** snapshot session stats BEFORE each attempt → run the attempt → snapshot AFTER → per-bucket deltas give the attempt's usage; prompt-side input is the sum of all three delivery buckets (raw + cacheRead + cacheWrite), minus `ΔassistantMessages × estimatedSystemPromptTokens` so multi-turn attempts aren't charged for the fixed system prompt on every call; outputs are plain deltas; every delta clamps at 0.
**Invariant:** comparability across providers comes from SUMMING the cache buckets into one prompt figure, never comparing raw `input` fields; fixed boilerplate must be subtracted per call or long system prompts dominate short tasks; negative deltas clamp to zero instead of propagating counter drift. The same four-bucket convention appears in the live cost probe (usage.input+cacheRead counted as tokIn) — keep the two consistent.
**Probe:** exercised via the stats-diff path in `runSingleTask` (`packages/metaharness/adapters/edit/runner.ts:1240-1248`); direct pins live in the summary tests `reports median/p1/p99 token stats` and `separates token stats for successfully one-shot tasks vs overall` (`adapters/edit/runner.test.ts:275-358`) which fix the resulting aggregates. Coverage caveat: the bucket-summing rule itself is source-read; its downstream aggregates are test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "diffTokenStats estimateTokens getSessionStats cacheRead cacheWrite assistantMessages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the accounting convention for any cross-model benchmark or spend tracker: sum delivery buckets, subtract per-call fixed overhead, clamp deltas, report `total=input+output`. Adapt the bucket names to your provider SDK and the ÷4 estimator to a real tokenizer; omit nothing else — the comment-documented rationale is the invariant that porters get wrong.
