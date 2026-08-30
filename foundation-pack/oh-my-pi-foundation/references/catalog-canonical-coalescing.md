<!-- capsule-v2 -->
# Canonical-id coalescing — how do 40 provider spellings of one model collapse into a single selector?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you map every variant spelling (`anthropic/claude-opus-4.8`, `us.anthropic.claude-opus-4-8`, `[Kiro] claude…`) onto ONE canonical id with a four-source provenance ladder?

## override → bundled/heuristic official match → preferred fallback → self
**Path/Symbol:** `packages/catalog/scripts/equivalence.ts:resolveCanonicalIdForModel` (:762), `getHeuristicCanonicalCandidates` (:708), `getPreferredFallbackCanonicalCandidate` (:737), `buildCanonicalModelIndex` (:843); marker vocab in `src/identity/markers.ts:CANONICAL_TRAILING_MARKER_PATTERN` (:43).
**Signature:** `buildCanonicalModelIndex(models, reference, equivalence?): CanonicalModelIndex {records, byId, bySelector}`; resolution returns `{id, source: "override"|"bundled"|"heuristic"|"fallback"}`.
**Data Shape:** candidate BFS queue expands cheap transforms (case/namespace/marker strip via the CANONICAL pattern — no `search`) then heavy ones; bounded FIFO memo (cap 4096, evict-oldest) caches per modelId; per-(reference,equivalence) WeakMap keyed on compiled config prevents cache poisoning.

### Decisive source
```ts
// Resolution results depend on (model, equivalence, reference); cache them on
// the reference data keyed by the compiled equivalence config so neither a
// different reference dataset NOR a different override set can poison entries.
let caches = referenceData[kResolutionCaches];
caches = new WeakMap(); caches.set(compiledEquivalence, new Map());

// Fallback candidates must be BARE lowercase family names (no / : .) —
// "claude-opus-4-8" qualifies, "openai/gpt-5.5" never does — and are only
// considered when the raw id actually contained separators.
const cleanCandidates = candidates.filter(candidate =>
  !candidate.includes("/") && !candidate.includes(":") &&
  candidate.toLowerCase() === candidate &&
  extractUpstreamFamilyCandidate(candidate)?.toLowerCase() === candidate);
```

**Flow:** explicit override wins → exclude list short-circuits to self → Anthropic/Claude alias ladders check official ids (dotted Bedrock profiles fold to canonical) → heuristic candidates intersect official ids + suffix aliases → best official match wins UNLESS a bare clean fallback outranks a namespaced match (`compareCandidatePreference`) → else bare fallback → else the id itself with source `"fallback"`; records group variants under canonical ids sorted by selector.
**Invariant:** (1) canonical coalescing uses the NARROWER trailing-marker vocabulary than proxy-reference lookup (`search` excluded — Perplexity's sonar-pro-search is a real distinct SKU here); (2) coalescing NEVER changes what's sent on the wire — it only re-keys selection/UI; (3) cache keys must include everything resolution reads (model fields + compiled config + reference identity).
**Probe:** direct `packages/catalog/test/descriptors.test.ts` + `test/variant-collapse.test.ts` exercise adjacent surfaces; equivalence itself is generator-side tooling consumed by scripts — coverage caveat: deterministic checks only (bounded memo + pure functions verified by construction). Nearest behavioral pins: `test/gateway-reference.test.ts` for the sibling lookup path.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildCanonicalModelIndex resolveCanonicalIdForModel heuristic candidates", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the provenance ladder (override/bundled/heuristic/fallback) and poisoning-proof cache keying for any multi-provider selector surface; adapt candidate transforms to your ecosystems; omit if you expose providers explicitly. Coverage caveat recorded above.
