<!-- capsule-v2 -->
# Tier resolution fall ladder — what happens when the chosen tier is not configured?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** A profile may configure only some of high/medium/low — how must an unavailable chosen tier be re-targeted without ever failing the turn?

## Fall-up-first resolver + throwing decision builder
**Path/Symbol:** `extensions/routing.ts:resolveAvailableTier` (lines 82–98) and `extensions/routing.ts:buildRoutingDecision` (lines 100–131).
**Signature:** `resolveAvailableTier(profile: RouterProfile, preferred: RouterTier): RouterTier`; `buildRoutingDecision(profileName, profile, tier, phase, reasoning, thinkingOverrides?, isClassifier?): RoutingDecision`.
**Data Shape:** `RouterProfile = { high?/medium?/low?: RoutedTierConfig }` — every tier optional. Resolution happens AFTER the budget downgrade, as the last mutation before building the decision.

### Decisive source
```ts
if (profile[preferred]) return preferred;
// Fall "up": low → medium → high
const order: RouterTier[] = ['low', 'medium', 'high'];
const startIdx = order.indexOf(preferred);
for (let i = startIdx + 1; i < order.length; i++) {
  if (profile[order[i]]) return order[i];
}
// Fall "down" as last resort
for (let i = startIdx - 1; i >= 0; i--) {
  if (profile[order[i]]) return order[i];
}
return preferred; // unreachable if profile has ≥1 tier
```
```ts
const routed = profile[tier];
if (!routed) throw new Error(`Profile "${profileName}" has no configuration for the ${tier} tier.`);
```

**Flow:** resolve → if the resolved tier differs, rewrite reasoning (`Resolved from X to Y tier (...) Original: ...`) AND re-derive phase via `phaseForTier(resolvedTier)` → build decision. The builder parses the canonical `provider/model` ref, defaults thinking per tier (high→'high', low→'low', else 'medium'), applies per-tier overrides, and stamps timestamp/flags.
**Invariant:** Quality degrades upward before it degrades downward — a missing medium prefers high over low. After resolution, `buildRoutingDecision`'s throw is a genuine invariant breach (empty profile), not a routine path.
**Probe:** `extensions/routing.test.ts` :165–190 (preferred kept / `{high}` + preferred low → high / `{low}` + preferred medium → low), :215–225 (`buildRoutingDecision` throws on missing tier).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "resolveAvailableTier fall up down", limit: 10 });
```

## Verdict
Adopt the asymmetric up-then-down scan and the post-resolution phase rewrite verbatim; adapt tier names/order to your ladder if it differs; omit the unreachable final return only with your language's totality checker satisfied. All three resolution arms and the throw are directly tested at this commit.
