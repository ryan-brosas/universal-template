<!-- capsule-v2 -->
# Model tokenizer resolution — how do you pick the right embedded tokenizer from an id alone?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Given a model id, which local tokenizer approximates its counts, and where is that decision allowed to live?

## Catalog-policy resolution baked onto the Model at build time
**Path/Symbol:** `packages/catalog/src/model-tokenizer.ts:claudeTokenizer` (:22), `qwenTokenizer` (:33), `deepSeekTokenizer` (:39), `kimiTokenizer` (:47), `glmTokenizer` (:53), `resolveModelTokenizer` (:62).
**Signature:** `resolveModelTokenizer(modelId): ModelTokenizer | undefined`; consumed ONLY by `buildModel` (`tokenizer: spec.tokenizer ?? resolveModelTokenizer(requestModelId ?? id)`).
**Data Shape:** bounded clear-at-2048 Map caching `ModelTokenizer | null` (null memoizes "no tokenizer"); ladder order claude → qwen → deepseek → kimi → glm.

### Decisive source
```ts
// Resolution is catalog policy, NOT a runtime caller heuristic: buildModel
// materializes the result as Model.tokenizer; consumers read that property.
// Distill ids are NOT v3-architecture ("distill" check precedes version
// matching); dated aliases pin exact tokenizers.
function claudeTokenizer(modelId) {
  const parsed = parseAnthropicModel(modelId);
  if (parsed) {
    if (parsed.kind === "opus") {
      if (semverGte(parsed.version, "5")) return "claude-v5";
      if (semverGte(parsed.version, "4.7")) return "claude-v47";
      return "claude-v3";
    }
    return semverGte(parsed.version, "5") ? "claude-v5-sonnet" : "claude-v3";
  }
  // Unparsed dotted/dashed claude ids fall back to v3 — the safe default.
  return /(^|[-/.:])claude([-.:]|$)/i.test(modelId) ? "claude-v3" : undefined;
}
```

**Flow:** bare id → classifier-backed ladders per family (qwen ≥3.5 ⇒ qwen3; deepseek v3/v4/r1 unless distill; kimi k2/k3 aliases incl. `kimi-for-coding*`; glm ≥5 ⇒ glm5) → first hit wins → cached.
**Invariant:** (1) explicit spec.tokenizer always wins over inference; (2) fallback for unparseable family members is the OLDEST tokenizer (undercount beats misclassifying architecture); (3) requestModelId (post-routing wire id) drives resolution so collapsed variants tokenize as their backing SKU.
**Probe:** direct `packages/catalog/test/model-tokenizer.test.ts:21` (ladder incl. alias and distill-exclusion cases).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveModelTokenizer claudeTokenizer qwen3", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt build-time tokenizer materialization with oldest-generation fallback; adapt ladders to your embedded tokenizers; omit entirely if you count tokens server-side. Coverage caveat: none.
