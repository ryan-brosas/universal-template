<!-- capsule-v2 -->
# Thinking-level derivation + clamp ladder — how are per-tier thinking capabilities computed once and enforced at stream time?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How should a router derive which thinking levels each tier supports at config time, then clamp user requests to them at runtime?

## Derive resolvedThinkingLevels once; walk DOWN the level ordinal to clamp
**Path/Symbol:** `extensions/config.ts:normalizeTierConfig` (:301–321 derivation), `extensions/config.ts:clampThinkingLevel` (:604–620), `extensions/config.ts:getUnsupportedTiers` (:585–598), `collectProfileThinkingLevels` (:567–579); enforcement consumers `provider.ts` :479–487 (streamSimple) and advisory consumers `commands.ts` :368–381 / `index.ts` :528–540.
**Signature:** `clampThinkingLevel(requested: ThinkingLevel, supported: ThinkingLevel[] | undefined): ThinkingLevel`; `getUnsupportedTiers(profile: RouterProfile, level: ThinkingLevel): string[]`.
**Data Shape:** Ordinal `THINKING_LEVELS = ['off','minimal','low','medium','high','xhigh','max']`; default supported set `DEFAULT_THINKING_LEVELS = ['high','medium','low']`. Derived set stored as `RoutedTierConfig.resolvedThinkingLevels`.

### Decisive source
```ts
const explicitThinkingLevels = tierThinkingLevels ?? aliasDefinition?.thinkingLevels;
const baseThinkingLevels: ThinkingLevel[] =
  explicitThinkingLevels ??
  (effectiveReasoning === false ? [] : [...DEFAULT_THINKING_LEVELS]);

// Auto-add the tier's thinking value ... only if the user didn't
// explicitly constrain the thinkingLevels array.
const resolvedThinkingLevels: ThinkingLevel[] = [...baseThinkingLevels];
if (!explicitThinkingLevels && thinking !== 'off' && !resolvedThinkingLevels.includes(thinking)) {
  resolvedThinkingLevels.push(thinking);
}
```
```ts
if (requested === 'off' || !supported || supported.length === 0) {
  return 'off';
}
const reqIdx = THINKING_LEVELS.indexOf(requested);
for (let i = reqIdx; i >= 0; i--) {
  if (supported.includes(THINKING_LEVELS[i])) return THINKING_LEVELS[i];
}
return 'off';
```

**Flow:** derivation precedence is explicit tier array > alias array > reasoning:false → empty > default trio; the tier's own `thinking` value is auto-appended ONLY when levels were not explicitly constrained (explicit arrays are authoritative). At stream time streamSimple clamps `(thinkingOverride ?? decision.thinking)` through the tier's resolved set before delegation. Downward-only clamping: a requested `xhigh` on a `['medium']`-only model yields `medium`, never an upgrade. `getUnsupportedTiers`/`collectProfileThinkingLevels` power advisory warnings ("X tiers may not support 'Y'") and the provider registration's `thinkingLevelMap` (xhigh/max only — provider.ts :215–225).
**Invariant:** Clamping never escalates capability; 'off' always passes through as 'off'; an empty/undefined supported set means 'off', not "unrestricted".
**Probe:** `extensions/config.test.ts` :418–447 (union collection incl. skip-without-levels), :449–485 (unsupported-tier lists incl. undefined resolvedThinkingLevels treated as unsupported); clamp ladder itself is source-pinned with consumer evidence at provider.ts :479–487.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "clampThinkingLevel resolvedThinkingLevels unsupported", limit: 10 });
```

## Verdict
Adopt derive-once/clamp-at-stream separation, the downward-only ordinal walk, and the explicit-array-is-authoritative rule verbatim; adapt the level names/order and the advisory-warning surface to your host; omit the xhigh/max-only thinkingLevelMap specialization if your host advertises all levels natively.
