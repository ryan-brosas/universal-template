<!-- capsule-v2 -->
# Embedding middleware wrapper — how do transformParams / wrapEmbed compose, and which override hooks can silently change batching behavior?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** In what order do multiple embedding middlewares apply, and what is the full hook surface (including the capability overrides that alter chunking)?

## Reverse-reduce composition
**Path/Symbol:** `packages/ai/src/middleware/wrap-embedding-model.ts:wrapEmbeddingModel` (:23–40) + `doWrap` (:42–100).
**Signature:** `wrapEmbeddingModel({ model: V3|V4, middleware: M | M[], modelId?, providerId? }): EmbeddingModelV4`.
**Data Shape:** middleware object = `{specificationVersion:'v4', transformParams?, wrapEmbed?, overrideProvider?, overrideModelId?, overrideMaxEmbeddingsPerCall?, overrideSupportsParallelCalls?}`.

### Decisive source
```ts
return [...asArray(middlewareArg)]
  .reverse()
  .reduce((wrappedModel, middleware) => {
    return doWrap({ model: wrappedModel, middleware, modelId, providerId });
  }, model);
```

**Flow:** array reversed then folded over the model — first-listed middleware's transformParams runs FIRST on params; last-listed wraps closest to doEmbed. Each `doWrap` produces a fresh V4-shaped plain object delegating to the wrapped model.
**Invariant:** the reversal makes declaration order read left-to-right while execution nests inside-out — porters who fold WITHOUT reversing flip both param-transform and wrap order. This mirrors wrapLanguageModel's contract (see default-injection-middlewares.md) but is a separate implementation for the embedding family.
**Probe:** `packages/ai/src/middleware/wrap-embedding-model.test.ts` (ordering cases); byte-exact `grep -n 'reverse()' packages/ai/src/middleware/wrap-embedding-model.ts` → single hit :36.

## Capability overrides change scheduler behavior
**Path/Symbol:** `packages/ai/src/middleware/wrap-embedding-model.ts:73–75`.
**Data Shape:** overrides are functions evaluated ONCE at wrap construction (`overrideX?.({model}) ?? model.X`), NOT per call.

### Decisive source
```ts
maxEmbeddingsPerCall:
  overrideMaxEmbeddingsPerCall?.({ model }) ?? model.maxEmbeddingsPerCall,
supportsParallelCalls:
  overrideSupportsParallelCalls?.({ model }) ?? model.supportsParallelCalls,
```

**Flow:** a middleware can force `maxEmbeddingsPerCall` (e.g. clamp a provider that lies about its limit) or flip `supportsParallelCalls`, and embedMany will honor those values because it reads them off the WRAPPED model.
**Invariant:** overriding capabilities is semantically load-bearing: setting `supportsParallelCalls:false` serializes an otherwise-parallel pipeline; raising `maxEmbeddingsPerCall` beyond the real API limit produces runtime rejections the middleware author owns. Porters who treat these as cosmetic metadata break batching (see embed-batching-parallelism.md for the consumer side).
**Probe:** `packages/ai/src/middleware/wrap-embedding-model.test.ts`; byte-exact `grep -n 'overrideMaxEmbeddingsPerCall' packages/ai/src/middleware/wrap-embedding-model.ts` → hits :49,:73.

## defaultEmbeddingSettingsMiddleware
**Path/Symbol:** `packages/ai/src/middleware/default-embedding-settings-middleware.ts:defaultEmbeddingSettingsMiddleware` (:11–22).
**Signature:** `({settings: Partial<{headers?, providerOptions?}>}) => EmbeddingModelMiddleware`.
**Data Shape:** only headers/providerOptions exist for embeddings — no settings/instructions like the language-model twin.

### Decisive source
```ts
transformParams: async ({ params }) => {
  return mergeObjects(settings, params) as EmbeddingModelV4CallOptions;
},
```

**Flow:** merges static settings under call params via mergeObjects' explicit-wins matrix (params beat defaults; null beats undefined — see micro-utility-kernels.md for mergeObjects internals).
**Invariant:** the embedding surface intentionally has ONLY two knobs; porting language-model default middleware wholesale would invent nonexistent settings.
**Probe:** `packages/ai/src/middleware/default-embedding-settings-middleware.test.ts`; byte-exact `grep -n 'mergeObjects(settings, params)' packages/ai/src/middleware/default-embedding-settings-middleware.ts` → single hit :19.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "wrapEmbeddingModel transformParams wrapEmbed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reverse-fold composition and the six-hook surface verbatim (same shape as language middleware — one mental model). Adapt identity/branding overrides (`providerId`/`modelId` constructor args win over middleware overrides) to your naming. Omit nothing; ~100 lines total. Direct tests cover ordering and overrides; runner unavailable here (no node_modules).
