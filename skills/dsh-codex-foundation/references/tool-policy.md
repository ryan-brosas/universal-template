<!-- capsule-v2 -->
# Live settings-backed policy — image-tool, Responses-API, and model-catalog preferences with a migration invariant

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how to keep one process-local policy object that (a) projects only browser-safe image-tool toggles, (b) holds Codex-only Responses-API experiment flags, (c) advertises a provider-ordered subset of a full model catalog, and (d) enforces a cross-provider tool gate at execution time — while migrating a retired `store:true` flag to WebSocket context reuse and never letting the browser mutate the full catalog?

## ImageToolPolicy
**Path/Symbol:** `src/tool-policy.ts:ImageToolPolicy` (class), `src/tool-policy.ts:constructor` (70-89), `src/tool-policy.ts:attach` (92-102), `src/tool-policy.ts:snapshot` (105-110), `src/tool-policy.ts:update` (119-127), `src/tool-policy.ts:responseApiSnapshot` (135-141), `src/tool-policy.ts:updateResponseApi` (143-153), `src/tool-policy.ts:modelCatalogSnapshot` (160-166), `src/tool-policy.ts:updateModelCatalog` (168-177), `src/tool-policy.ts:assertAllowed` (179-187), `src/tool-policy.ts:replace` (189-198), `src/tool-policy.ts:normalizeModels` (200-204), `src/tool-policy.ts:preferenceSchema` (55-64), `src/tool-policy.ts:DEFAULT_IMAGE_TOOL_PREFERENCES` (38-41), `src/tool-policy.ts:DEFAULT_RESPONSE_API_PREFERENCES` (45-48). Graph-resident as `dsh-codex.src.tool-policy.ImageToolPolicy.*`.
**Signature:** `class ImageToolPolicy { constructor(base: Partial<OpenAICodexPreferences> = {}, modelCatalog: readonly ModelCatalogEntry[] = []); attach(ctx: Context): void; snapshot(): ImageToolPreferences; update(patch): Promise<ImageToolPreferences>; responseApiSnapshot(): ResponseApiPreferences; updateResponseApi(patch): Promise<ResponseApiPreferences>; modelCatalogSnapshot(): ModelCatalogSettings; updateModelCatalog(patch): Promise<ModelCatalogSettings>; assertAllowed(exec: ToolExecution, tool: 'imagegen'): void }`.
**Data Shape:** `OpenAICodexPreferences` = `ImageToolPreferences & ResponseApiPreferences & ModelCatalogPreferences & { useStatefulResponses: boolean }`. `ImageToolPreferences` = `{ modifyReadImage: boolean; shareImagegenWithOtherModels: boolean }`. `ResponseApiPreferences` = `{ useWebSocketContextReuse: boolean; useNativeCompaction: boolean }`. `ModelCatalogEntry` = `{ id: string; name: string }`; `ModelCatalogSettings` = `{ availableModels: ModelCatalogEntry[]; models: string[] }`. Defaults keep generic vision-model interoperability on (`modifyReadImage:true`, `shareImagegenWithOtherModels:true`) and the stateless Harness behavior conservative (`useWebSocketContextReuse:false`, `useNativeCompaction:false`, `useStatefulResponses:false`). `snapshot`/`responseApiSnapshot`/`modelCatalogSnapshot` all return detached projections (spread copies), never the live `current` object.

### Decisive source
```ts
// src/tool-policy.ts — migration invariant + execution-time gate + catalog normalization
constructor(base: Partial<OpenAICodexPreferences> = {}, modelCatalog: readonly ModelCatalogEntry[] = []) {
  this.modelCatalog = modelCatalog.map(model => ({ ...model }))
  this.current = {
    ...DEFAULT_IMAGE_TOOL_PREFERENCES,
    ...DEFAULT_RESPONSE_API_PREFERENCES,
    useStatefulResponses: false,
    ...base,
    models: this.normalizeModels(base.models ?? this.modelCatalog.map(model => model.id)),
  }
  if (this.current.useStatefulResponses && base.useWebSocketContextReuse === undefined) {
    this.current = { ...this.current, useWebSocketContextReuse: true }
  }
}

// Execution-time cross-provider gate: Codex always allowed, others gated by the toggle
assertAllowed(exec: ToolExecution, tool: 'imagegen'): void {
  const configured = exec.agent?.session.requestHeader()?.config
  const provider = configured?.provider ?? exec.agent?.options.provider
  if (provider === OPENAI_CODEX_PROVIDER) return
  if (!this.current.shareImagegenWithOtherModels) {
    throw new Error(`${tool} is disabled for models outside the openai-codex provider in Settings`)
  }
}

// replace: re-apply migration + normalize models, fire image watchers only on image change
private replace(next: OpenAICodexPreferences): void {
  next = next.useStatefulResponses && !next.useWebSocketContextReuse
    ? { ...next, useWebSocketContextReuse: true } : next
  next = { ...next, models: this.normalizeModels(next.models) }
  const imageChanged = next.modifyReadImage !== this.current.modifyReadImage
    || next.shareImagegenWithOtherModels !== this.current.shareImagegenWithOtherModels
  this.current = next
  if (imageChanged) { for (const listener of this.imageWatchers) listener() }
}

// Catalog subset is the INTERSECTION of the requested ids and the full catalog (provider-ordered)
private normalizeModels(models: readonly string[]): string[] {
  const selected = new Set(models)
  return this.modelCatalog.filter(model => selected.has(model.id)).map(model => model.id)
}
```

**Flow:** (1) `attach(ctx)` registers a `settingsNamespace('openai-codex')` scope with `preferenceSchema(this.current.models)` (`applies:'live'`, base = current), then `replace(scope.get())` and `scope.watch(next => this.replace(next))`; the `ctx.effect` teardown unwatches and clears `this.scope`. (2) Every `update*` method throws `'OpenAI Codex settings service is unavailable'` when `this.scope === undefined` (not attached), else calls `scope.update(patch)`, then `this.replace(scope.get())`, and returns the detached snapshot. (3) `updateResponseApi` additionally writes `useStatefulResponses:false` whenever `useWebSocketContextReuse` is being set explicitly (the migration key is retired once the explicit flag is chosen). (4) `updateModelCatalog` normalizes the requested ids against the full catalog and persists only the intersection. (5) `assertAllowed` resolves the provider from the request-header config first, then `agent.options.provider`; the owning provider is always allowed, others throw only when `shareImagegenWithOtherModels` is false. (6) `replace` re-applies the migration invariant and model normalization on every incoming live update, and notifies `imageWatchers` only when an image-tool preference actually changed.
**Invariant:** the migration `useStatefulResponses:true` (and no explicit `useWebSocketContextReuse`) always yields `useWebSocketContextReuse:true` — in the constructor and in every `replace`; the browser can never mutate the full catalog (only the intersection of requested ids with `modelCatalog` is ever persisted, and all snapshots are detached copies); Codex imagegen access is never blocked by the cross-provider toggle, but other providers are blocked when `shareImagegenWithOtherModels` is false; image watchers fire exactly once per real image-preference change.
**Probe:** `tests/tool-policy.spec.ts` — "persists independent live toggles through the dsh settings seam" (snapshot + responseApiSnapshot defaults, then `update` + `updateResponseApi`), "notifies the read_image enhancer when its live setting changes" (watcher fires once), "migrates the retired store:true preference to WebSocket context reuse" (constructor + responseApiSnapshot), "keeps Codex imagegen access while applying its toggle to another provider" (`assertAllowed`), "persists a provider-ordered model discovery subset without affecting the full catalog" (`modelCatalogSnapshot` + `updateModelCatalog`), and "defaults an older partial settings document to the complete model catalog" (seed `{useNativeCompaction:true}` → models default to all catalog ids, native compaction preserved).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", query: "ImageToolPolicy settings preference model catalog assertAllowed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single `ImageToolPolicy` object as the live settings-backed policy hub: register one settings scope, keep a private `current` that is replaced wholesale from live updates, expose only detached browser projections, re-apply the migration invariant on every `replace`, and gate a cross-provider tool at execution time by resolving the provider from the request header first. Adapt the namespace, the exact preference keys, and the migration flag names to the target provider; the `assertAllowed` provider resolution (request-header config then `agent.options.provider`) is the portable pattern for any "owning provider always allowed, others gated" rule. Omit the `@deepseek-ai/dsh-settings`/`@deepseek-ai/cordis`/`@deepseek-ai/schemastery` specifics and the `OPENAI_CODEX_PROVIDER` route constant when porting to another provider. Coverage: `src/tool-policy.ts` and `tests/tool-policy.spec.ts` both `no_recorded_issue` + `metadata_match`; the vitest runner is not installed in this read-only checkout, so deterministic probes were executed against the actual source (Node strip-types, external imports stubbed) and matched every constructor/`assertAllowed`/`normalizeModels`/migration assertion (defaults, `useStatefulResponses:true` → `useWebSocketContextReuse:true`, Codex allowed while other-provider throws, catalog intersection preserving provider order).
