<!-- capsule-v2 -->
# Alias-then-canonical two-stage resolution — how do user-friendly model names expand to provider/model refs without a second grammar?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How should shorthand aliases (`gpt4`) and literal refs (`openai/gpt-4o`) coexist in tier models, fallback lists, and classifier config?

## Exact-key alias lookup, pass-through otherwise
**Path/Symbol:** `extensions/config.ts:resolveModelRef` (:78–87); alias-map validation in `extensions/config.ts:normalizeModelsMap` (:152–215); application sites in `extensions/config.ts:normalizeTierConfig` (:239–250 tier model, :264–278 fallbacks) and `normalizeConfig` (:419–449 classifierModel).
**Signature:** `resolveModelRef(ref: string, models: Record<string, ModelDefinition> | undefined): { canonicalRef: string; definition?: ModelDefinition }`.
**Data Shape:** `ModelDefinition = {model, contextWindow?, maxTokens?, reasoning?, thinkingLevels?}` (types.ts :16–22). Alias keys live in one flat map; the definition rides along so defaults can inherit.

### Decisive source
```ts
const definition = models?.[ref];
if (definition) {
  return { canonicalRef: definition.model, definition };
}
return { canonicalRef: ref };
```
```ts
// normalizeTierConfig — alias resolution + validation gate per reference
const resolved = resolveModelRef(rawModel, models);
try {
  parseCanonicalModelRef(resolved.canonicalRef);
  parsedModel = resolved.canonicalRef;
} catch (error) { /* warning + tier disabled */ }
```

**Flow:** stage 1 resolves alias→canonical (exact key; no fuzzy match) and carries the definition; stage 2 re-validates the canonical result through `parseCanonicalModelRef`. The same pair runs at three sites: the tier's primary model (invalid → tier disabled), each fallback entry individually (invalid → that entry warned+dropped, tier SURVIVES), and both classifierModel forms. Aliases themselves are validated against the identical grammar inside normalizeModelsMap before the map is usable.
**Invariant:** After normalization, every stored model string is canonical `provider/model` — runtime code never sees an alias. An invalid reference degrades to a warning at the narrowest possible scope (entry < tier < profile).
**Probe:** `extensions/config.test.ts` :122–138 (alias resolves with definition attached; non-alias passes through untouched), :245–263 (tier model aliased, valid fallback kept, `'invalid-fallback'` dropped with warning while tier stays defined).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "resolveModelRef alias canonical definition", limit: 10 });
```

## Verdict
Adopt the two-stage resolve-then-validate pattern and the narrowest-scope degradation ladder verbatim; adapt the definition fields your host needs on an alias (context window, reasoning support); omit fuzzy matching deliberately — exact-key only keeps normalization deterministic.
