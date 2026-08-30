<!-- capsule-v2 -->
# Warn-and-degrade normalization — how does config validation reject bad input without ever rejecting the user?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** What is the contract for normalizing partially-invalid user config so the extension still starts with the valid remainder?

## One warnings array; degradation at the narrowest scope
**Path/Symbol:** `extensions/config.ts:normalizeTierConfig` (:217–335) and `extensions/config.ts:normalizeConfig` (:337–472).
**Signature:** `normalizeTierConfig(value: unknown, profileName: string, tier: RouterTier, warnings: string[], models?): RoutedTierConfig | undefined`; `normalizeConfig(raw: RouterConfig): ConfigLoadResult`.
**Data Shape:** Both push human-readable strings into ONE caller-owned `warnings` array. Output tier is `RoutedTierConfig | undefined` (undefined = tier disabled); output carries raw optional fields PLUS baked `resolvedContextWindow/resolvedMaxTokens/resolvedThinkingLevels`.

### Decisive source
```ts
if (!rawModel) {
  warnings.push(`Profile "${profileName}" ${tier} tier is missing a model. Tier disabled.`);
  return undefined;
}
```
```ts
if (!high && !medium && !low) {
  warnings.push(`Profile "${name}" has no valid tiers. Skipped.`);
  continue;
}
```
```ts
const phaseBias = typeof raw.phaseBias === 'number'
  ? Math.max(0, Math.min(1, raw.phaseBias)) : 0.5;
```

**Flow:** models map normalizes FIRST (aliases must exist before tiers resolve); each tier independently returns undefined on missing/unparseable model; a profile whose three tiers are all undefined is skipped entirely; `phaseBias` clamps to [0,1] with default 0.5 (clamped, NOT rejected); `maxSessionBudget` requires >0 else undefined; rules lacking valid `matches`/tier are dropped with a JSON-stringized warning; classifier thinking degrades to undefined with a warning. Present-but-invalid numerics are distinguished from absent ones (`entry.contextWindow !== undefined && !contextWindow` warns only in the former case). Result shape `{config, warnings}` keeps every message attributable.
**Invariant:** normalizeConfig NEVER throws and NEVER drops an entire valid portion because an unrelated field was invalid; each warning names its profile/tier/field. The empty-model case is fatal only for that one tier, and three dead tiers kill only that one profile.
**Probe:** `extensions/config.test.ts` :226–264 (non-object → undefined; missing model → warning+undefined; alias + invalid fallback → defined result, 1 warning), :266–300 (full normalizeConfig clean run), :487–527 (classifier object variants: valid thinking kept / invalid warned+undefined / missing model field warned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "normalizeConfig warnings tier disabled skipped", limit: 10 });
```

## Verdict
Adopt the warn-and-degrade contract verbatim: never throw from normalization, degrade at entry < tier < profile scope, clamp numeric scalars instead of rejecting them; adapt warning routing (here strings returned to the caller, not logged) to your host's notification surface; omit nothing — the present-vs-absent distinction for invalid fields prevents spurious warnings and is directly tested.
