<!-- capsule-v2 -->
# Resolved-config store with live overlay — how a stream function gets config it wasn't handed, without stale geometry

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** A low-level stream helper needs resolved model config (reasoning map, generation caps, protocol) that lives above its layer — do you pass it down through every call site or read a store, and how do you keep the store from going stale?

## Resolved-config store with live overlay
**Path/Symbol:** `src/stream.ts:76-86` (`KimiStreamRuntimeConfig`, `resolvedStore`, `setStoreResolvedKimiConfig`); consumption + fallback + overlay `streamSimpleKimi` :240-269; seeding site `reloadEffectiveKimiRuntimeConfig` index.ts:141-148 (via `resolveKimiModelConfig` src/models.ts:146-166).
**Signature:** `setStoreResolvedKimiConfig(config: KimiStreamRuntimeConfig): void` — setter only; no getter is exported, the store is read inside the same module.
**Data Shape:** `KimiStreamRuntimeConfig = { model: KimiResolvedModelConfig; protocol: "openai"|"anthropic"; uploads: {thresholdBytes} }`; module-global `resolvedStore: KimiStreamRuntimeConfig | null = null`.

### Decisive source
```ts
const streamConfig = resolvedStore ?? {
  model: {
    contextWindow: model.contextWindow,
    maxTokens: model.maxTokens,
    input: ["text"],
    reasoning: model.reasoning,
    reasoningMap: {},
    thinkingKeep: null,
    generation: {},
  },
  protocol: ENV_KIMI_CODE_PROTOCOL,
  uploads: DEFAULT_KIMI_CODE_CONFIG.uploads,
};
const modelConfig: KimiResolvedModelConfig = {
  ...streamConfig.model,
  contextWindow: model.contextWindow,
  maxTokens: model.maxTokens,
  input: [...model.input],
  reasoning: model.reasoning,
  supportsThinkingType:
    discoveredModel.supportsThinkingType ?? (model.reasoning ? undefined : "no"),
  supportEfforts: discoveredModel.supportEfforts
    ? [...discoveredModel.supportEfforts]
    : undefined,
```

**Flow:** whenever config is (re)loaded — cwd change, trust change, settings save —
`reloadEffectiveKimiRuntimeConfig` derives `KimiResolvedModelConfig` via
`resolveKimiModelConfig` (server extras override contextWindow when positive;
`supportsThinkingType !== "no"` drives reasoning, falling back to a plain
supportsReasoning boolean; image/video booleans merge into the input array; effort lists
are copied defensively) and pushes it into the stream module's store. At request time the
stream reads the store, or falls back to conservative defaults if never seeded
(`input:["text"]`, `thinkingKeep:null`, empty reasoningMap/generation). Then the overlay:
the live `model` object's geometry (contextWindow/maxTokens/input/reasoning) always wins
over whatever the store captured, so a mid-session window growth can't serve stale caps.
**Invariant:** the store carries only what the Model object cannot express (reasoningMap,
generation overrides, thinkingKeep, protocol, upload threshold); everything dimensional is
re-overlaid per request. Unseeded store ⇒ safe degraded stream, not a crash.

**Probe:** direct source anchors — index.ts:134-148 seeds the store on every reload with
the freshly validated config; stream.ts:240-252 fallback literal; :259-269 overlay keys.
No dedicated unit test isolates this seam at pin (the store's consumers are covered by the
extension-registration and payload suites); recorded as a coverage caveat, evidence is
whole-range source reads.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "resolved store stream runtime config overlay fallback", limit: 5 });
// observed: setStoreResolvedKimiConfig #1 (-30.95), KimiStreamRuntimeConfig #3 (-19.19)
```

## Verdict
Adopt the store-plus-overlay split when a low layer needs high-layer config: store the
semantic extras, re-derive dimensions from live objects each call. Adapt the fallback
literal to safe values for your endpoint. Omit the store entirely if you can thread config
through arguments everywhere — but note this repo chose the store because the stream entry
is reached through host-controlled dispatch it doesn't own.
