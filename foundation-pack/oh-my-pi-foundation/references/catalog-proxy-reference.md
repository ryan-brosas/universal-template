<!-- capsule-v2 -->
# Proxy reference lookup — how do you inherit bundled metadata for a reseller's renamed model id?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Given `[Kiro] claude-opus-4-8` or `gpt-5.4:cloud` on a custom provider, how do you find the upstream catalog entry to inherit pricing/limits while keeping the custom transport?

## Candidate-ladder resolution over an exact+suffixAlias index with winner ranking
**Path/Symbol:** `packages/catalog/src/identity/reference.ts:buildModelReferenceIndex` (:58), `shouldReplaceReference` (:34), `getReferenceCandidateIds` (:96), `inheritReferenceThinking` (:145), `resolveModelReference` (:157); `identity/bundled.ts` lazy 12k-model walk; `identity/id.ts:getBracketStrippedModelIdCandidates` (:60).
**Signature:** `resolveModelReference(modelId, index: {exact, suffixAlias}): Model | undefined`; `inheritReferenceThinking(current, ref, provider): ThinkingConfig | undefined`.
**Data Shape:** candidate queue expands: bracket-stripped forms (both-ends → leading-only → trailing-only, full-width `【】` supported) → model-like segments (family-prefix regex + must contain a digit, longest-first) → `:cloud`/`-cloud` suffix strip → last `/` segment → colon→dash → lowercase → trailing-marker strip; all deduped via insertion-order Set used as a FIFO.

### Decisive source
```ts
// Portkey/gateway wire ids (`@provider/model`) are opaque — fuzzy matching
// would map them to unrelated bundled entries (@modal/GLM-5-2-FP8 →
// devin/glm-5-2). Tested: gateway-reference.test.ts:11.
if (modelId.startsWith("@")) return undefined;

// Winner ranking when several catalog rows share a normalized id: larger
// limits first, then cache-pricing completeness, then first-party OpenAI.
// xai-oauth subscription entries carry ZERO public pricing and inflated
// maxTokens — excluded outright so they can't outrank paid references.
function isZeroCostXaiOAuthReference(candidate) { /* all four cost fields === 0 */ }

// Wire routing is PROVIDER-specific: cross-provider inheritance can rewrite
// gateway ids (Portkey @modal/GLM-5-2-FP8 → devin glm-5-2). Same-provider only.
if (reference.provider !== provider) return undefined;
```

**Flow:** build the index once lazily over ~12k bundled models (the walk triggers thinking enrichment, so it's deferred off module load) → resolve walks candidates in most-stripped-first order, exact map before suffixAlias → hit returns the bundled row for metadata inheritance only (`requestModelId`/transport stay custom) → thinking config inherits ONLY same-provider.
**Invariant:** (1) canonical-id coalescing and reference lookup are DIFFERENT modules with different marker vocabularies — reference may strip `search` (`sonar-pro-search` proxy id inherits upstream pricing without becoming `sonar-pro`; Perplexity's real distinct SKU keeps its identity in canonical resolution); (2) bracketed affixes are wrapper tags, stripped only as CANDIDATES, never mutating the caller's id; (3) fuzzy segment extraction requires BOTH a known family prefix AND a digit — free text never matches.
**Probe:** direct `packages/catalog/test/gateway-reference.test.ts:9` (@-prefix opacity + cross-provider non-inheritance), `test/model-id-affixes.test.ts:46` (bracket ladder order incl. full-width brackets), `test/siliconflow-provider.test.ts` / `gmi-cloud-provider.test.ts` (proxy id inheritance in situ).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveModelReference buildModelReferenceIndex getBracketStrippedModelIdCandidates", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the candidate-ladder + ranked-index design and the strict separation from canonical coalescing; adapt the marker vocabulary to your ecosystem's suffix fashions; omit suffixAlias if your ids never drop namespaces. Coverage caveat: none for the core; bundled-index walk itself is exercised indirectly through the 12k-row fixture.
