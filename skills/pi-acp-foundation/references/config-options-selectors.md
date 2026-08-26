<!-- capsule-v2 -->
# Config options — model/thinking selectors built from pi state with null-model degradation

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter expose "pick a model" and "pick thinking level" as ACP session config options, and what exactly happens when pi reports no models or an unknown current model?

## Selector plumbing
**Path/Symbol:** `src/acp/agent.ts` — `isThinkingLevel` (:1313-1315), `getThinkingState` (:1317-1354), `getSessionConfiguration` (:1356-1381), `buildConfigOptions` (:1383-1430), `getModelState` (:1432-1497), `emitConfigOptionsUpdate` (:1499-1515), `setSessionModel` (:1517-1552).
**Signature:** `getSessionConfiguration(proc, pre?): Promise<{configOptions, models, modes}>`; `buildConfigOptions({models, modes}): SessionConfigOption[]`; `setSessionModel(proc, requestedModelId): Promise<void>`.
**Data Shape:** models `{availableModels: AdvertisedModel[], currentModelId: string} | null`; modes `{availableModes: {id,name,description?}[], currentModeId: string}`; config option `{type:'select', id, category, name, description, currentValue, options:[{value,name,description}]}`. IDs: `MODEL_CONFIG_ID='model'`, `THOUGHT_LEVEL_CONFIG_ID='thought_level'`.

### Decisive source
```ts
// getModelState degradation ladder
if (!availableModels.length && !currentModelId) return null          // BOTH missing → no Model selector at all
if (!currentModelId) currentModelId = availableModels[0]?.modelId ?? 'default'  // unknown current → FIRST listed
// getThinkingState
let current: ThinkingLevel = 'medium'                                 // default when state unreadable
const tl = typeof state?.thinkingLevel === 'string' ? state.thinkingLevel : null
if (tl && isThinkingLevel(tl)) current = tl                           // INVALID value silently falls back to medium
// buildConfigOptions — model option goes FIRST only when non-empty
if (state.models?.availableModels.length) configOptions.unshift({ type:'select', id: MODEL_CONFIG_ID, ... })
```
```ts
// setSessionModel accepts BOTH id shapes
if (requestedModelId.includes('/')) {
  const [candidateProvider, ...rest] = requestedModelId.split('/')
  provider = candidateProvider; modelId = rest.join('/')   // 'provider/rest/of/id' — split on FIRST slash ONLY
} else {
  // bare 'model': resolve provider via available-models lookup; NOT FOUND → RequestError.invalidParams
}
```

**Flow:** `getSessionConfiguration` runs `getModelState` + `getThinkingState` in parallel, both accepting a `pre` snapshot (state captured earlier in newSession) so the same RPC isn't re-issued. Every pi read is try/catch→null so a broken RPC degrades to defaults instead of failing session/new. Model identity is the composite `` `${provider}/${id}` `` (display name `` `${provider}/${name}` ``) because bare ids collide across providers. After a successful `setSessionConfigOption`, `emitConfigOptionsUpdate` re-reads everything fresh and pushes a `config_option_update` sessionUpdate so the client UI stays in sync.

**Invariant:** the thinking list is STATIC (`off|minimal|low|medium|high|xhigh`) — it is not derived from pi state; only the current value is. An invalid stored level must fall back to `'medium'`, not throw or pass through. The Model selector is OMITTED entirely (not shown disabled) when pi offers zero models and no current model. `rest.join('/')` matters: model ids may themselves contain slashes; splitting on every slash corrupts them.

**Probe:** `test/unit/session-config-options.test.ts` — "newSession returns configOptions for model and thinking selectors" pins the FULL deepEqual payload (model first, thought_level second, `currentValue:'test/beta'` / `'high'`, all six thinking options); "setSessionConfigOption maps model changes to pi and emits config_option_update" pins the write path + re-emit.
**Coverage:** agent.ts `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "getSessionConfiguration buildConfigOptions getModelState setSessionModel", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the selector construction order, the null-models→omit-selector rule, first-listed fallback for unknown current, static six-level thinking table with medium fallback, and first-slash-only model-id parsing. Adapt category names to your client's schema. Omit nothing.
