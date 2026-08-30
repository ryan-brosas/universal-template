<!-- capsule-v2 -->
# Summarizer output budget — why reasoning models return empty summaries

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** What maxOutputTokens should a summarizer request use so thinking models still emit summary text?

## Cap-not-target ladder: explicit config wins; model metadata only ever LOWERS
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction-shared.ts:693-754` (`resolveSummaryMaxOutputTokens`, `resolveSummarizerConfig`).
**Signature:** `resolveSummaryMaxOutputTokens(config: ProviderConfig) → number`; `resolveSummarizerConfig({activeProviderConfig, summarizer?}) → ProviderConfig`.
**Data Shape:** `DEFAULT_SUMMARY_MAX_OUTPUT_TOKENS = 4_096`. Ladder: explicit `config.maxOutputTokens` → else `min(4096, model maxTokens)` (from `modelInfo.maxTokens` or `knownModels[modelId].maxTokens`) → else 4096.

### Decisive source
```ts
// The summarizer output budget is a cap, not a target: reasoning models need
// headroom beyond their thinking output or no summary text ever arrives and
// compaction is skipped. An explicit configuration wins as-is; otherwise the
// default applies, with model metadata (maxTokens is reported capability,
// not a product default) only ever lowering it.
```
```ts
if (config.providerId === "openai-codex") {
    const { maxOutputTokens: _maxOutputTokens, ...rest } = config;
    return { ...rest, thinking: false };
}
```

**Flow:** resolve summarizer provider config — explicit summarizer spec overlays its own base providerConfig ONLY when providerIds match (else credentials/URL come from the overlay alone); then defaults applied: non-Codex gets computed maxOutputTokens + `thinking:false` (summaries never pay for reasoning); Codex OAuth requests strip maxOutputTokens entirely (provider rejects it). Empty text + reasoningChars>0 ⇒ diagnosed as `output_budget_consumed_by_reasoning`, compaction skipped.
**Invariant:** Model-reported maxTokens NEVER raises the budget above 4096 — reported capability ≠ product default; thinking disabled at the request level, not by prompt.
**Probe:** `grep -cF 'providerId === "openai-codex"' .../compaction-shared.ts` → 1; `grep -cF 'thinking: false,' .../compaction-shared.ts` → 2; upstream tests "resolves the summarizer output budget from explicit config, else the default clamped by model metadata", "does not add unsupported max output tokens to Codex OAuth summarizer requests".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "resolveSummaryMaxOutputTokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cap-only-lowers semantics and thinking-off summaries; adapt the 4096 default and Codex carve-out to host provider set. Runner blocked honestly; battery greps green.
