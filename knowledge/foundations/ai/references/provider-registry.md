<!-- capsule-v2 -->
# Provider registry — how do `"provider:model"` composite ids resolve across seven model types without letting a missing separator masquerade as a provider id?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you build a string-keyed multi-provider registry that resolves `providerId:modelId` ids for every model family, applies registry-level middleware only where it exists, and reports WHICH id half was wrong?

## createProviderRegistry + DefaultProviderRegistry
**Path/Symbol:** `packages/ai/src/registry/provider-registry.ts:createProviderRegistry` (:137-168) + class `DefaultProviderRegistry` (:175-410); error types `no-such-provider-error.ts` and `@ai-sdk/provider`'s `NoSuchModelError`.
**Signature:** `createProviderRegistry<PROVIDERS, SEPARATOR=':'>(providers: PROVIDERS, { separator?, languageModelMiddleware?, imageModelMiddleware? } = {}): ProviderRegistryProvider<PROVIDERS, SEPARATOR>`; accessors `languageModel/embeddingModel/imageModel/transcriptionModel/speechModel/rerankingModel/videoModel(id: `${key}${SEPARATOR}${string}`)` plus `files(id)`/`skills(id)`.
**Data Shape:** private `providers: Partial<Record<keyof PROVIDERS, ProviderV4 & { videoModel? }>>` filled at construction via `registerProvider({id, provider})` (`Object.entries` loop :160-165); v2/v3 providers normalized once through `asProviderV4`.

### Decisive source
```ts
private splitId(id: string, modelType: RegistryModelType): [string, string] {
  const index = id.indexOf(this.separator);            // FIRST occurrence, not last
  if (index === -1) {
    throw new NoSuchModelError({
      modelId: id,
      modelType,
      message:
        `Invalid ${modelType} id for registry: ${id} ` +
        `(must be in the format "providerId${this.separator}modelId")`,
    });
  }
  return [id.slice(0, index), id.slice(index + this.separator.length)];
}
// accessor pattern (languageModel shown; embedding/transcription/speech/reranking identical minus middleware):
let model = this.getProvider(providerId, 'languageModel').languageModel?.(modelId);
if (model == null) throw new NoSuchModelError({ modelId: id, modelType: 'languageModel' });
if (this.languageModelMiddleware != null) {
  model = wrapLanguageModel({ model, middleware: this.languageModelMiddleware });
}
```

**Flow:** split on FIRST separator → `getProvider(providerId)` throws `NoSuchProviderError` carrying `availableProviders: Object.keys(this.providers)` when absent → optional-chained factory call `provider.X?.(modelId)` → null result throws `NoSuchModelError` naming the FULL original id → only for language/image models is the registry-level middleware applied via `wrapLanguageModel`/`wrapImageModel`.
**Invariant:** (1) Splitting uses `indexOf` so MODEL ids containing the separator survive (`'should return language model with additional colon from provider'`, test :52; custom multi-char separators tested :125/:159) — a porter who splits on the LAST separator or `split(sep)[1]` breaks model ids like `gpt-4:preview`. (2) The two failure classes are DIFFERENT errors keyed by which half failed: unknown provider → `NoSuchProviderError` (with available list), known provider + missing model or malformed id → `NoSuchModelError` (tests :77/:86/:116). (3) Middleware wraps ONLY language and image models — embedding/transcription/speech/rerank/video return raw models even when middlewares were configured; silently extending wrapping to other families changes behavior for ports. (4) `files(id)`/`skills(id)` take a BARE provider key (no separator) and throw plain `Error`s with actionable text when unsupported (:385-409). (5) Video models are converted lazily: `registerProvider` binds the provider's own `videoModel` into a prototype-cloned wrapper returning `asVideoModelV4(...)` (:216-223), and `videoModel()` accessor re-wraps (:382) so v3 models surface as v4 ON DEMAND (test :622 'should convert v3 video models to v4 on demand').
**Probe:** `bash -c "grep -c NoSuchProviderError $REFERENCE_ROOT/ai/packages/ai/src/registry/provider-registry.ts && grep -n indexOf $REFERENCE_ROOT/ai/packages/ai/src/registry/provider-registry.ts"` → `2` and `245:    const index = id.indexOf(this.separator);`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createProviderRegistry splitId getProvider NoSuchProviderError", limit: 5 });
// → ai.packages.ai.src.registry.provider-registry.createProviderRegistry Function packages/ai/src/registry/provider-registry.ts 137-168
```

## Verdict
Adopt first-separator splitting, the two-error taxonomy with available-providers listing, and lazy v3→v4 video conversion verbatim. Adapt the middleware families to your model-type set (wrap only the families your host has middleware for). Omit the deprecated `experimental_createProviderRegistry` alias (:173).
