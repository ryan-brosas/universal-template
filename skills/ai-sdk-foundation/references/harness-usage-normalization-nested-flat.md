<!-- capsule-v2 -->
# Harness nested-usage normalization — how do V4 nested token counters become flat `LanguageModelUsage` without NaN-poisoning totals?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your wire usage is `{inputTokens:{total,noCache,cacheRead,cacheWrite}, outputTokens:{total,text,reasoning}}` but your result surface and telemetry expect flat fields plus a `totalTokens` sum — what's the exact collapse and the missing-counter rule?

## Shape-sniffing normalizer with null-preserving addition

**Path/Symbol:** `packages/harness/src/agent/internal/turn-telemetry.ts` — `normalizeUsage` (:116–156), `addTokenCounts` (:107–114); consumers: `inferenceEnd` (:270–296) and `end` (:423–479) normalize every usage before dispatching onStepEnd/onEnd; the result-object side uses ai-core `asLanguageModelUsage` + `addLanguageModelUsage` for the same boundary (harness-stream-text-result.ts :260, :357).
**Signature:** `normalizeUsage(usage: unknown): LanguageModelUsage | unknown`; `addTokenCounts(a?: number, b?: number): number | undefined`.
**Data Shape:** in (V4 nested): `{inputTokens:{total,noCache?,cacheRead?,cacheWrite?}, outputTokens:{total,text?,reasoning?}, raw?}` → out (flat): `{inputTokens, inputTokenDetails:{noCacheTokens,cacheReadTokens,cacheWriteTokens}, outputTokens, outputTokenDetails:{textTokens,reasoningTokens}, totalTokens, raw}`.

### Decisive source
```ts
// :107–114 — BOTH-null stays undefined; one-sided null coerces to 0.
// Missing counters can never fabricate a number, but they also can't poison the sum.
function addTokenCounts(a: number | undefined, b: number | undefined) {
  return a == null && b == null ? undefined : (a ?? 0) + (b ?? 0);
}
// :116–124 — shape sniff first: anything without BOTH inputTokens+outputTokens objects
// passes through UNCHANGED (already-flat or foreign shapes are not errors)
if (usage == null || typeof usage !== 'object' ||
    !('inputTokens' in usage) || !('outputTokens' in usage)) return usage;
...
return {
  inputTokens: input.total,
  inputTokenDetails: { noCacheTokens: input.noCache,
    cacheReadTokens: input.cacheRead, cacheWriteTokens: input.cacheWrite },
  outputTokens: output.total,
  outputTokenDetails: { textTokens: output.text, reasoningTokens: output.reasoning },
  totalTokens: addTokenCounts(input.total, output.total),
  raw: (usage as {raw?}).raw,
};
```

**Flow:** harness finish-step/finish events carry provider-shaped usage → normalizeUsage flattens once at the telemetry boundary → dispatcher events always see the flat LanguageModelUsage shape integrations read; non-conforming values degrade to pass-through instead of throwing so a weird runtime can't kill telemetry.
**Invariant:** Normalization is best-effort BY SHAPE, never by try/catch; `totalTokens` is undefined iff BOTH sides are undefined (contrast with embedMany's deliberate `{tokens: NaN}` under-reporting poison — different plane, different contract); detail keys rename (noCache→noCacheTokens, cacheRead→cacheReadTokens, text→textTokens) rather than nest.
**Probe:** deterministic content probes at pin: :111–113 both-null ternary byte-exact; :120 `'inputTokens' in usage` double-membership guard byte-exact; direct test fixture `turn-telemetry.test.ts:5–13` exercises exactly this nested shape through stepFinish/end (read-verified @pin; runner block stands). Companion: embed-batching-parallelism.md owns the NaN-poison counterpoint on the retrieval plane.
**Retrieve:** `search_graph { project:"ai", query:"normalize nested usage tokens flat totalTokens cacheRead reasoning", limit:3 }` → rank#2 `turn-telemetry.normalizeUsage :116–156` between two unrelated-plane twins (verified live @pin).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.turn-telemetry.normalizeUsage" });
```

## Verdict
Adopt shape-sniffing pass-through + null-preserving summation for any multi-shape usage surface; adapt detail-key names to your host type; do NOT port the NaN default here — it belongs only to cost ledgers that must make under-reporting visible.
