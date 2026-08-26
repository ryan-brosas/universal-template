<!-- capsule-v2 -->
# Capacity precedence + honest reporting — how does a virtual router model advertise a context window it may not stream into?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** What contextWindow/maxTokens should a fake router model report when its tiers resolve to different real models?

## API registry > tier config > alias > hardcoded default; report max, enforce actual
**Path/Symbol:** `extensions/config.ts:resolveContextWindow` (:515–534) / `resolveMaxTokens` (:542–561); registration consumer `extensions/provider.ts` :190–237; enforcement consumer `extensions/provider.ts` :461–471.
**Signature:** `resolveContextWindow(tier: RouterTier, profile: RouterProfile, modelRegistry: ExtensionContext['modelRegistry'] | undefined): number`.
**Data Shape:** Pre-resolved values were baked into `RoutedTierConfig.resolvedContextWindow/resolvedMaxTokens` during normalization (tier > alias > DEFAULT_CONTEXT_WINDOW/DEFAULT_MAX_TOKENS). The registry lookup is the only runtime-variable source.

### Decisive source
```ts
if (modelRegistry) {
  try {
    const { provider, modelId } = parseCanonicalModelRef(tierConfig.model);
    const registryModel = modelRegistry.find(provider, modelId);
    if (registryModel?.contextWindow) return registryModel.contextWindow;
  } catch { /* ignore */ }
}
// 2-4. Pre-resolved during config normalization (tier > alias > hardcoded)
return tierConfig.resolvedContextWindow ?? DEFAULT_CONTEXT_WINDOW;
```
```ts
// provider.ts — reported capacity is the MAX across the profile's tiers
let maxContextWindow = DEFAULT_CONTEXT_WINDOW;
for (const tier of ROUTER_TIERS) {
  if (!profile[tier]) continue;
  const cw = resolveContextWindow(tier, profile, state.currentModelRegistry);
  if (cw > maxContextWindow) maxContextWindow = cw;
}
// ... "The honesty check + truncateContext handles the case where the
//      actually routed model is smaller."
```

**Flow:** per attempt in streamSimple, the ACTUAL tier limit is re-resolved through the same chain; if it is smaller than the advertised `model.contextWindow`, `truncateContext(context, targetLimit)` shrinks the payload before delegation. Registry lookup errors are swallowed by design — a broken registry degrades to baked values, never to a failed turn.
**Invariant:** Advertised capacity must be ≥ any tier's enforceable capacity (max-across-tiers guarantees it), and every delegated request must be truncated to the routed tier's real limit before the provider call. A missing tier falls to the hardcoded default rather than undefined.
**Probe:** `extensions/config.test.ts` :346–381 (registry wins; registry-absent → pre-resolved), :383–416 additional coverage (missing tier → defaults 128_000/16_384; registry model without values → pre-resolved; parseCanonicalModelRef throw inside lookup → falls through to resolved values).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "resolveContextWindow resolveMaxTokens registry default", limit: 10 });
```

## Verdict
Adopt the four-source precedence chain and the report-max/enforce-actual pairing verbatim; adapt DEFAULT_CONTEXT_WINDOW/DEFAULT_MAX_TOKENS and the registry interface (`find(provider, modelId)`) to your host; omit the silent try/catch only if your registry cannot throw — here swallowing is deliberate fail-open posture.
