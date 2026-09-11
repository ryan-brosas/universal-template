<!-- capsule-v2 -->
# OpenAI-compat wire-quirk compat — how do 40 host quirks become one resolved record instead of scattered if-chains?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How should a multi-host chat-completions client encode per-endpoint dialects (thinking formats, reasoning replay, tool-choice limits, stream floors) without per-request detection?

## Detect-once flag record + conditional whenThinking variant view
**Path/Symbol:** `packages/catalog/src/compat/openai.ts:buildOpenAICompat` (:292), `detectStreamMarkupHealingPattern` (:112), `hasLocalLoopbackBaseUrl` (:264), `OPENCODE_WHEN_THINKING` (:164), `xaiResponsesReasoningEffortMap` (:190), `buildOpenAIResponsesCompat` (:699), `buildOpenRouterCompat` (tail: chat ∪ responses-only projection).
**Signature:** `buildOpenAICompat(spec): ResolvedOpenAICompat`; `buildOpenRouterCompat(spec)` composes both surfaces via `pickResponsesOnly`.
**Data Shape:** ~45 flags incl. `{supportsStore, supportsDeveloperRole, supportsMultipleSystemMessages, thinkingFormat: zai|kimi|openrouter|qwen|qwen-chat-template|openai, reasoningDisableMode, maxTokensField, requiresReasoningContentForToolCalls, allowsSyntheticReasoningContentForToolCalls, replayReasoningContent, qwenPreserveThinking, qwenTemplateReasoningEffort, wireModelIdMode, toolSchemaFlavor: moonshot-mfjs|grammar, streamIdleTimeoutMs, streamFirstEventTimeoutMs, effortMap}`.

### Decisive source
```ts
// OpenCode gateways 400 BOTH ways on reasoning_content (#1071 too much,
// #1484 missing) — so the base compat leaves replay OFF and a conditional
// variant reactivates it only for thinking-engaged requests. The synthetic
// default is force-disabled there or the reply lands in the wrong key.
const OPENCODE_WHEN_THINKING = {
  requiresReasoningContentForToolCalls: true,
  allowsSyntheticReasoningContentForToolCalls: false,
  reasoningContentField: "reasoning_content",
};

// Local llama.cpp-style servers re-tokenize the whole prompt every request;
// KV-cache reuse survives only if prior `<think>` blocks are replayed
// verbatim (#3528). NOT gated on spec.reasoning: discovery hardcodes
// reasoning:false for these backends, but the stream parser still records
// thinking deltas — gating on the flag would leave every local Qwen
// re-triggering full prompt processing.
replayReasoningContent: isLocalOpenAICompatBackend,

// The proxy carve-out (litellm) skips REPLAY but NOT the timeout floor —
// widening an idle ceiling never pushes a wire field, so a loopback litellm
// fronting a cold llama-server must not abort prefill at 100s (#4786).
const isLocalServingBackend = isLocalOpenAICompatBackend || hasLocalLoopbackBaseUrl(baseUrl);
```

**Flow:** host booleans detected once (`modelMatchesHost`) → single flags object assembled with inline rationale comments citing issue numbers → sparse overrides applied → post-detection repairs (direct DeepSeek `extraBody.thinking` removed since `reasoningDisableMode` covers it; omitReasoningEffort forced when unsupported; Kimi-K3/MiMo effort maps merged under user's) → conditional `whenThinking` policy materialized as a COMPLETE alternate compat view (deepseek direct forces `thinking:{type:"enabled"}`; opencode applies OPENCODE_WHEN_THINKING) so request handlers just pick base-or-variant by thinking state.
**Invariant:** (1) provider id beats URL because it's explicitly configured; (2) system-message coalescing allowlist exists for KV-cache reuse but Qwen-family templates FORCE coalescing everywhere (their template ships with the weights — every vLLM/SGLang host hits it); (3) Kimi ids trigger MFJS schema flavor on ANY host because proxies forward `tools.function.parameters` verbatim to Moonshot's validator; (4) official-OpenAI endpoint heals NOTHING (structured reasoning never leaks) to avoid misfiring on legitimate fences.
**Probe:** direct `packages/catalog/test/build.test.ts:375+` (wireModelIdMode ladder, DeepSeek token stripping, forced-tool downgrades #436/:481, Mistral bridge :508, cumulative MiniMax deltas :534, loopback litellm floor :580, healer isolation :610, breakpoint TTL :660), `test/issue-6664-repro.test.ts`, xAI suppression block :269–375.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildOpenAICompat thinkingFormat replayReasoningContent streamIdleTimeoutMs", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the detect-once/flag-record/variant-view architecture and the loopback heuristics; adapt individual quirk flags to your endpoint matrix (each encodes a live 400 you'd otherwise rediscover); omit Mistral/NVIDIA-specific fields if absent. Coverage caveat: none — build.test.ts is 1,401 lines.
