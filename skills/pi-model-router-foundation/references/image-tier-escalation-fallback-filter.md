<!-- capsule-v2 -->
# Image tier escalation + capability-filtered fallback chain — how are image attachments forced onto a capable model without losing the decision trail?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** When the routed tier cannot accept images, what is the exact escalation order and how does the executed chain stay consistent with it?

## Two-layer capability gate in the consumer
**Path/Symbol:** `extensions/provider.ts:streamSimple` — decision rebuild (lines 346–396) and executed-chain filter (lines 416–425); helper `checkModelSupportsImage` (:347–355).
**Signature:** `checkModelSupportsImage(modelRef: string): boolean` via `registry.find(...)?.input?.includes('image') ?? false` (parse failure ⇒ false).
**Data Shape:** Capability comes from the host registry's `model.input` array, not config. Tier escalation ladder: `low → ['medium','high']`, `medium → ['high']`, `high → []`.

### Decisive source
```ts
if (imageAttached) {
  const tierModels = [decision.targetLabel, ...(profile[decision.tier]?.fallbacks ?? [])];
  if (!tierModels.some(checkModelSupportsImage)) {
    const tiersToTry: RouterTier[] =
      decision.tier === 'low' ? ['medium', 'high'] : decision.tier === 'medium' ? ['high'] : [];
    ...
    if (foundTier) {
      decision = buildRoutingDecision(model.id, profile, foundTier, phaseForTier(foundTier),
        `Forced ${foundTier} tier because the originally routed ${decision.tier} tier does not support image attachments.`,
        state.thinkingByProfile[model.id], false);
    }
  }
}
...
let modelsToTry = [...new Set([decision.targetLabel, ...(profile[decision.tier]?.fallbacks ?? [])])];
if (imageAttached) {
  modelsToTry = modelsToTry.filter(checkModelSupportsImage);
  if (modelsToTry.length === 0) modelsToTry = [decision.targetLabel];
}
```

**Flow:** layer 1 — if NO model of the decided tier (primary + fallbacks) accepts images, escalate to the first higher configured tier whose chain has an image-capable model and REBUILD the decision with an explicit `Forced ... tier ...` reasoning; layer 2 — independently of any rebuild, filter the deduped execution chain down to image-capable models; if that empties the chain, restore `[decision.targetLabel]` as a degenerate last resort rather than skipping the turn.
**Invariant:** Escalation is upward-only and never silently drops the original reasoning — it is replaced by a string naming both tiers. The two layers are deliberately redundant: layer 1 preserves a truthful `RoutingDecision` for status/debug/persistence; layer 2 guarantees per-model safety even when only some fallbacks are capable.
**Probe:** `extensions/provider.test.ts` :302–357 — medium tier (`gpt-4o-mini` + `gemini-1.5-flash`) text-only, high (`gpt-4o`) image-capable, image attached, pinned medium ⇒ final `tier === 'high'` and reasoning contains `'Forced high tier because the originally routed medium tier does not support image attachments'`. Degenerate-restore branch (:420–425) is source-pinned without a dedicated test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "image attachment forced tier checkModelSupportsImage", limit: 10 });
```

## Verdict
Adopt the capability predicate shape (`input.includes('image')`, fail-closed on lookup/parse errors), the upward-only tier ladder, and the dual decision-rebuild + chain-filter layers; adapt the capability source to your model catalog field; omit the degenerate restore only if your host tolerates zero-capable chains differently than failing the turn.
