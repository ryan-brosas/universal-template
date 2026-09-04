<!-- capsule-v2 -->
# Single-profile adapter factory — how do you assemble a single-profile adapter that layers wrapper behavior through late-bound closures without forking the generic adapter?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How do you assemble a single-profile adapter that layers wrapper behavior through late-bound closures without forking the generic adapter?

## One-entry profiles map over the public pi-ai extension points
**Path/Symbol:** `src/adapter.ts:createOpenAICodexAdapter` (`:166-190`); constants it consumes: `OPENAI_CODEX_STREAM_IDLE_TIMEOUT_MS :23` (300_000) and `OPENAI_CODEX_RETRY_POLICY :68-72`; subclass wiring `OpenAICodexAdapter :131-158`.
**Signature:** `function createOpenAICodexAdapter(credentials: OpenAICodexCredentialStore, resolveAttachments: () => AttachmentStore | undefined, responsePreferences: () => ResponseApiPreferences, fastMode?: FastModeRegistry, visibleModelIds?: () => readonly string[]): PiAiAdapter`.
**Data Shape:** Builds ONE profiles entry keyed `OPENAI_CODEX_PROVIDER`: `{ displayName: 'OpenAI Codex', streamIdleTimeoutMs: 300_000, retryPolicy: OPENAI_CODEX_RETRY_POLICY, configuredMaxTokens: new Map() (EMPTY), piProvider: responses.wrap(requestProvider(provider, fastMode)) }`. Binds credential state via `createModels({ credentials })` + `models.setProvider(provider)`; returns `new OpenAICodexAdapter({ profiles: () => profiles, resolveApiKey, resolveAttachments }, responses, visibleModelIds)`.

### Decisive source
```ts
// src/adapter.ts :173-189
const provider = openaiCodexProvider()
const responses = new OpenAICodexResponseRuntime(responsePreferences)
const profiles = new Map<string, ResolvedPiAiProviderProfile>([[OPENAI_CODEX_PROVIDER, {
  provider: OPENAI_CODEX_PROVIDER,
  displayName: 'OpenAI Codex',
  streamIdleTimeoutMs: OPENAI_CODEX_STREAM_IDLE_TIMEOUT_MS,
  retryPolicy: OPENAI_CODEX_RETRY_POLICY,
  configuredMaxTokens: new Map(),
  piProvider: responses.wrap(requestProvider(provider, fastMode)),
}]])
const models: MutableModels = createModels({ credentials })
models.setProvider(provider)
return new OpenAICodexAdapter({
  profiles: () => profiles,
  resolveApiKey: async () => (await models.getAuth(OPENAI_CODEX_PROVIDER))?.auth.apiKey,
  resolveAttachments,
}, responses, visibleModelIds)
```

**Flow:** Provider layering composes inside-out: vendored `openaiCodexProvider()` → `requestProvider` (OAuth-as-apiKey auth + fast-mode payload decoration) → `responses.wrap` (Codex-native transport/compaction choice). The adapter options are THREE zero-arg closures (`profiles`, `resolveApiKey`, `resolveAttachments`) so registration never freezes request-time state; `resolveApiKey` routes through `models.getAuth` while each request's resolver reads `credential?.key` — TWO token paths, ONE store.
**Invariant:** Never fork the generic adapter — layer behavior by wrapping the provider object and overriding the small adapter surface (listModels filter / stream purpose-marking live in OpenAICodexAdapter); `configuredMaxTokens` stays EMPTY so per-model caps are not silently narrowed here; exported constants let tests pin policy identity rather than re-derived copies.
**Probe:** `tests/adapter.spec.ts` — retry-policy identity+shape (`providerRetryPolicy(OPENAI_CODEX_PROVIDER)).toBe(OPENAI_CODEX_RETRY_POLICY)` with `{maxRetries:5, initialDelayMs:1_000, maxDelayMs:30_000, jitterRatio:0.2}`), omitted-vs-empty model list distinction, advertise≠resolve visibility.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "^dsh-codex\\.src\\.adapter\\.(requestProvider|createOpenAICodexAdapter|openAICodexModelCatalog)$", limit: 10 });
// observed live: total 3, has_more=false — createOpenAICodexAdapter :166-190 (in=2/out=8: callers index.apply + spec)
```
Graph-noise caveat proven this pass family: name-level traces on generic verbs (`adapter.resolve`) return cross-module collisions; trust snippet caller fields and qn-anchored probes instead.

## Verdict
Adopt one-entry-profile assembly with closure-based late binding and wrapper stacking for adding provider-native behavior to an existing generic adapter. Adapt profile field names/idle/retry values to host SPI. Omit Codex transport wrapping specifics (owned by responses-transport-choice). Coverage caveat: check_index_coverage clean for src/adapter.ts + tests/adapter.spec.ts; full suite baseline recorded in the work record.
