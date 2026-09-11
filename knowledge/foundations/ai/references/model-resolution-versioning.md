<!-- capsule-v2 -->
# String-model resolution & version-lifting — where does `embed('my-model')` actually resolve, and how do v2/v3 models become v4 without a copy?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How are bare string model ids resolved (and to WHERE), and what is the exact v2→v3→v4 lifting mechanism that preserves prototype methods?

## String ids fall through to the global default provider or the gateway
**Path/Symbol:** `packages/ai/src/model/resolve-model.ts:resolveEmbeddingModel` (:48–63), `resolveRerankingModel` (:186–214), `getGlobalProvider` (:216–219).
**Signature:** `resolveEmbeddingModel(model: string | EmbeddingModelV4|V3|V2): EmbeddingModelV4`; same shape for rerank (v3|v4 only).
**Data Shape:** input union includes plain strings; output is always a concrete V4 object.

### Decisive source
```ts
function getGlobalProvider(): ProviderV4 {
  const provider = globalThis.AI_SDK_DEFAULT_PROVIDER ?? gateway;
  return asProviderV4(provider);
}
```

**Flow:** string → `getGlobalProvider().embeddingModel(id)` (or optional `.rerankingModel?.(id)`) → else provider-object path checks `specificationVersion ∈ {v4,v3,v2}` (rerank: `{v4,v3}`) and throws `UnsupportedModelVersionError` carrying provider/modelId/version.
**Invariant:** there is NO local registry on this path — a bare string with no `globalThis.AI_SDK_DEFAULT_PROVIDER` set goes to the REMOTE GATEWAY package by default. This is a network side effect hiding behind a type union; porters who implement strings as "must be pre-registered locally" change failure modes (throw vs HTTP call). Reranking is the ONE family whose provider method is OPTIONAL: missing method ⇒ explicit error suggesting `gateway.rerankingModel("model-id")`, and its accepted spec versions exclude v2.
**Probe:** `packages/ai/src/model/resolve-model.test.ts:201–233` ('should return a gateway embedding model' asserts `provider==='gateway'`; global-provider block swaps in customProvider and asserts it wins); byte-exact `grep -cF 'globalThis.AI_SDK_DEFAULT_PROVIDER ?? gateway' packages/ai/src/model/resolve-model.ts` → 3.

## Proxy-based version lifting
**Path/Symbol:** `packages/ai/src/model/as-embedding-model-v4.ts:asEmbeddingModelV4` (:8–27); twin `as-reranking-model-v4.ts:asRerankingModelV4` (:4–17).
**Signature:** `(model: V2|V3|V4) => EmbeddingModelV4` / `(model: V3|V4) => RerankingModelV4`.
**Data Shape:** identity for v4; otherwise a `Proxy` whose `get` traps exactly one property.

### Decisive source
```ts
// first convert v2 to v3, then proxy v3 as v4:
const v3Model =
  model.specificationVersion === 'v2' ? asEmbeddingModelV3(model) : model;

return new Proxy(v3Model, {
  get(target, prop: keyof EmbeddingModelV3) {
    if (prop === 'specificationVersion') return 'v4';
    return target[prop];
  },
}) as unknown as EmbeddingModelV4;
```

**Flow:** v4 returns as-is → v3 wrapped in a one-property-override proxy → v2 first lifted to v3 (which emits a v2-compatibility warning via `logV2CompatibilityWarning`) then proxied.
**Invariant:** NOTHING is copied — methods keep their original binding and prototype (`this` inside doEmbed still points at the v2/v3 implementation), which is why "preserve prototype methods" is an explicit test. The proxy intercepts ONLY reads of `specificationVersion`, so any future property needing translation must be added to the trap, not assumed. The v2 lift carries an upstream TODO admitting unmapped properties may break — treat v2 as best-effort passthrough, not a real adapter layer.
**Probe:** `packages/ai/src/model/as-embedding-model-v4.test.ts:93` ('should convert v2 through v3 to v4' asserts specificationVersion==='v4' with provider/modelId preserved) + `packages/ai/src/model/resolve-model.test.ts:72` ('preserve prototype methods'); byte-exact `grep -n "if (prop === 'specificationVersion') return 'v4'" packages/ai/src/model/as-embedding-model-v4.ts` → single hit :18.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "resolveEmbeddingModel resolveRerankingModel specificationVersion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gateway-fallback resolution semantics (string = remote default unless a global provider is installed) and the one-property proxy lift verbatim — both are load-bearing compatibility machinery reused across ALL seven model families. Adapt the error-message text to your host's provider naming. Omit the speech/video special cases here (they bypass ProviderV4 and read `globalThis.AI_SDK_DEFAULT_PROVIDER` raw — covered as a pattern note only; mine separately if a multimodal porting question emerges). Direct tests pin gateway fallback, global-provider override, and prototype preservation; runner unavailable here (no node_modules).
