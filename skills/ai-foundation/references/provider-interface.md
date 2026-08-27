<!-- capsule-v2 -->
# Spec-versioned provider seam — how do you publish one integration surface that dozens of provider packages implement without ever breaking the deployed ones?

**Source:** Vercel AI SDK (Apache-2.0) `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the minimal contract a provider must implement, how do middlewares wrap it, and how does the core keep v2/v3 providers alive?

## LanguageModelV4: two operations, spec-versioned
**Path/Symbol:** `packages/provider/src/language-model/v4/language-model-v4.ts:LanguageModelV4` (lines 8–61).
**Signature:**
```ts
type LanguageModelV4 = {
  readonly specificationVersion: 'v4';
  readonly provider: string;
  readonly modelId: string;
  supportedUrls: PromiseLike<Record<string, RegExp[]>> | Record<string, RegExp[]>;
  doGenerate(options: LanguageModelV4CallOptions): PromiseLike<LanguageModelV4GenerateResult>;
  doStream(options: LanguageModelV4CallOptions): PromiseLike<LanguageModelV4StreamResult>;
};
```
**Data Shape:** The whole integration surface is TYPE-ONLY (`@ai-sdk/provider` ships no runtime). Exactly TWO operations return higher-level output parts, never raw provider payloads. `supportedUrls` maps media-type patterns (`*\/*`, `audio/*`, `application/pdf`) to RegExp arrays matched against LOWER-CASE URLs; matched URLs are natively handled and never downloaded.

### Decisive source
```ts
/**
 * Generates a language model output (non-streaming).
 *
 * Naming: "do" prefix to prevent accidental direct usage of the method
 * by the user.
 */
doGenerate(
  options: LanguageModelV4CallOptions,
): PromiseLike<LanguageModelV4GenerateResult>;
```
(`language-model-v4.ts:40–48`, verbatim)

**Flow:** provider package implements `LanguageModelV4` → core resolves it through `resolveLanguageModel` → only `doGenerate`/`doStream` are ever invoked.
**Invariant:** breaking changes ship as a NEW parallel version (`LanguageModelV2/V3/V4` coexist in the same package; middleware mirrors them as `language-model-v{2,3,4}-middleware.ts`) — never as edits to a shipped version. A porter who adds a field to an existing version breaks every deployed provider.
**Probe:** `packages/ai/src/middleware/wrap-language-model.test.ts` (:12 pass-through defaults, :25 `overrideModelId`, :134 `transformParams` called for `doGenerate`, :169 `wrapGenerate`) exercises the contract end-to-end through the public wrapper.

## Middleware: identity overrides + params transform + operation wrapping
**Path/Symbol:** `packages/provider/src/language-model-middleware/v4/language-model-v4-middleware.ts:LanguageModelV4Middleware` (lines 11–84); applied by `packages/ai/src/middleware/wrap-language-model.ts:wrapLanguageModel` (lines 25–42, `doWrap` 44–113).
**Signature:** `wrapLanguageModel({ model, middleware: M | M[], modelId?, providerId? }): LanguageModelV4`.
**Data Shape:** hooks — `overrideProvider`/`overrideModelId`/`overrideSupportedUrls` (identity), `transformParams({type:'generate'|'stream', params, model})` (pre-call mutation), `wrapGenerate`/`wrapStream({doGenerate, doStream, params, model})` (post-transform wrapping).

### Decisive source
```ts
const model = asLanguageModelV4(inputModel);
return [...asArray(middlewareArg)]
  .reverse()
  .reduce((wrappedModel, middleware) => {
    return doWrap({ model: wrappedModel, middleware, modelId, providerId });
  }, model);
```
```ts
async doGenerate(params) {
  const transformedParams = await doTransform({ params, type: 'generate' });
  const doGenerate = async () => await model.doGenerate(transformedParams);
  const doStream = async () => await model.doStream(transformedParams);
  return wrapGenerate
    ? await wrapGenerate({ doGenerate, doStream, params: transformedParams, model })
    : await doGenerate();
}
```
(`wrap-language-model.ts:32–38, 82–93`, verbatim)

**Flow:** array reversed → first middleware transforms input first, LAST wraps directly around the model → each `doGenerate`/`doStream`: transformParams → build BOTH thunks → invoke wrap hook if present else fall through. Explicit `modelId`/`providerId` args beat middleware overrides which beat the wrapped model's values.
**Invariant:** the wrap hooks receive the original operations as UNINVOKED thunks (`() => …`), both built from the same transformed params — a gateway middleware can switch call shapes (e.g. fall back to `doStream` inside `wrapGenerate`) lazily without losing either path. Wrapping with eagerly-invoked values kills the fallback path.
**Probe:** `wrap-language-model.test.ts` :296–491 (multiple middlewares: transformParams sequence order for doGenerate/doStream, wrapGenerate/wrapStream chaining order, middleware array not mutated).

## ProviderV4 + core-side version adaptation
**Path/Symbol:** `packages/provider/src/provider/v4/provider-v4.ts:ProviderV4` (lines 13–95); `packages/ai/src/model/resolve-model.ts:resolveLanguageModel` (31–46); `packages/ai/src/model/as-language-model-v4.ts` (whole, 25 L).
**Signature:** `resolveLanguageModel(model: LanguageModel): LanguageModelV4`; `asLanguageModelV4(model: V2|V3|V4): LanguageModelV4`.
**Data Shape:** `ProviderV4` requires `languageModel`/`embeddingModel`/`imageModel` (throw `NoSuchModelError` on unknown id); `transcriptionModel`/`speechModel`/`rerankingModel`/`files`/`skills` are OPTIONAL methods. DRIFT vs older docs: there is NO `realtimeModel` and NO `batch` at HEAD, and unsupported modalities are absent methods — not factories returning null.

### Decisive source
```ts
export function asLanguageModelV4(model): LanguageModelV4 {
  if (model.specificationVersion === 'v4') return model;
  // first convert v2 to v3, then proxy v3 as v4:
  const v3Model =
    model.specificationVersion === 'v2' ? asLanguageModelV3(model) : model;
  return new Proxy(v3Model, {
    get(target, prop) {
      if (prop === 'specificationVersion') return 'v4';
      return target[prop];
    },
  }) as unknown as LanguageModelV4;
}
```
(`as-language-model-v4.ts`, verbatim; `resolveLanguageModel` accepts `['v4','v3','v2']`, else `UnsupportedModelVersionError`; bare strings resolve via `globalThis.AI_SDK_DEFAULT_PROVIDER ?? gateway`)

**Flow:** user passes v2/v3/v4 model or string → resolve → upgrade chain v2→v3→Proxy-stamped-v4 → core treats everything as V4. Version-adaptation cost is paid ONCE in the core adapters (`as-*-v3/v4`), not N times across provider packages.
**Invariant:** the Proxy lies about exactly one property (`specificationVersion`) and delegates everything else — an adapter must not deep-copy or rewrap behavior, or provider-specific internals (streams, metadata) break.
**Probe:** `wrap-language-model.test.ts:262` ("should support models that use `this` context in supportedUrls" — proves the wrapper delegates, not copies).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "doGenerate doStream language model", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ai", name_pattern: "^(LanguageModelV4|LanguageModelV4Middleware|ProviderV4|wrapLanguageModel|resolveLanguageModel|asLanguageModelV4)$", detail: "ids" });
```

## Verdict
Adopt the two-operation spec-versioned interface, the reverse-reduce middleware composition with thunk-passed originals, optional-method provider discovery, and the single Proxy-based version adapter. Adapt media-type URL tables, provider ids, and the global-provider fallback to host. Omit the concrete ~70 provider packages and the experimental speech/video translation resolvers unless a target needs them. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2 — all cited ranges read at HEAD this session; claims are source-grounded.
