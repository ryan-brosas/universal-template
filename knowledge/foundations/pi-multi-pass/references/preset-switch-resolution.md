<!-- capsule-v2 -->
# Preset/switch resolution — how does switching accounts preserve the current model id, and how do preset activations fall back without partial state?
**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** When a user (or a preset) changes the active account, how do you guarantee the landing spot is authenticated and has a real model — and keep the user's current model id when possible?

## Auth-gated options + three-rung model ladder + fail-continue preset entries
**Path/Symbol:** `extensions/multi-sub.ts`: `normalizeSwitchAllowedProviderNames` (2776-2781), `getSwitchableProviderOptions` (2783-2812), `resolveSwitchTargetModel` (2814-2839), `handleSubsSwitch` (2841-2895), `handlePresetActivate` (5226-5281), `getBaseProvider` (1864-1871).
**Signature:** `function resolveSwitchTargetModel(ctx: ExtensionContext | ExtensionCommandContext, providerName: string, preferredModelId?: string): Model<Api> | undefined`; options are `{ providerName, label, description }[]`.
**Data Shape:** option filters = exact allow-list Set (trim/dedupe; empty-after-normalize -> unrestricted undefined) + authStorage.hasAuth + seen-dedup; base providers listed before `${provider}-${index}` subscriptions.

### Decisive source
```ts
// three-rung ladder: auth gate -> preferred id under SUB name -> base-provider walk
if (!ctx.modelRegistry.authStorage.hasAuth(providerName)) return undefined;
if (preferredModelId) {
  const preferred = ctx.modelRegistry.find(providerName, preferredModelId);
  if (preferred) return preferred as Model<Api>;
}
const baseProvider = getBaseProvider(providerName); // strips -N only if remainder is a template
if (!baseProvider) return undefined;
for (const baseModel of getModels(baseProvider as any) as Model<Api>[]) {
  const candidate = ctx.modelRegistry.find(providerName, baseModel.id);
  if (candidate) return candidate as Model<Api>;
}
return undefined;
// handleSubsSwitch passes the CURRENT model id so account switches keep it:
const nextModel = resolveSwitchTargetModel(ctx, selected.providerName, ctx.model?.id);
if (ctx.model?.provider === nextModel.provider && ctx.model?.id === nextModel.id) { /* no-op notify */ }
const success = await pi.setModel(nextModel);
if (!success) { /* error notify; selection unchanged */ }
// handlePresetActivate: ordered fail-continue entry ladder
for (const entry of preset.entries) {
  if (!entry.enabled) continue;
  if (!ctx.modelRegistry.authStorage.hasAuth(entry.provider)) continue;
  const model = ctx.modelRegistry.find(entry.provider, entry.model);
  if (!model) continue;
  const success = await pi.setModel(model);
  if (!success) continue;
  /* announce + setStatus */ return;
}
/* one warning: no entry usable */
```

**Flow:** allow-list normalization (project config only; trim/dedupe; all-blank means unrestricted) -> option build (SUPPORTED_PROVIDERS first, then merged+normalized subscriptions; each candidate must pass allow-list membership, hasAuth, and dedup) -> requested name must be an EXACT member of that list or it is rejected -> resolver ladder picks the model (current-id preservation first, then first base-template model re-findable under the sub clone name) -> identical provider+model short-circuits as a no-op -> `pi.setModel` boolean checked before any success claim. Presets run the same gates per ordered entry and stop at the FIRST successful setModel; exhausting every entry emits a single warning with no state written.
**Invariant:** a switch never lands on an unauthenticated provider or an unregistered model; preferred-model-first preserves the user's model identity across accounts; a failed setModel leaves selection untouched (no half-switch); preset activation is all-or-nothing per entry with no cascading writes.
**Probe:** `node tests/subs-switch-check.mjs` (pins preferred-model hit gpt-5.4 under openai-codex-2; base-fallback to gpt-5.3-codex when the preferred id is absent from the sub's list; allow-list filtering to exactly ["openai-codex-2"]). Green at b9d9d1d7a092.
**Coverage note:** extensions/multi-sub.ts and tests/subs-switch-check.mjs indexed FULL, no_recorded_issue, generation match 2026-08-24T14:18:05Z; cited ranges read directly from source at the pin. The check script is a behavioral twin (dependency-injected hasAuth/providerModels/baseProviderLookup), not a direct import.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "resolveSwitchTargetModel getSwitchableProviderOptions", limit: 3 });
```

## Verdict
Adopt the resolution ladder (auth gate -> preferred id under target identity -> base-template walk), the exact-membership guard on requested targets, the no-op guard, and the checked setModel result; adopt presets as ordered fail-continue ladders with all-or-nothing entries. Adapt modelRegistry/authStorage lookups to your host. Omit the TUI select wrapper (showWrappedSelect) and ~/.pi config paths.
