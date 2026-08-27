<!-- capsule-v2 -->
# Gateway modality model family — what do embedding/image/video/reranking/speech twins share with the language model, and where do they deliberately differ?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** When porting one gateway modality, which parts are copy-stable across all seven and which are per-modality contracts?

## Shared skeleton, per-modality deltas
**Path/Symbol:** `packages/gateway/src/gateway-embedding-model.ts` (whole, `doEmbed` :60+), `gateway-image-model.ts`, `gateway-video-model.ts`, `gateway-reranking-model.ts`, `gateway-speech-model.ts` — pattern mined once via the embedding twin (provider-twin ruling).
**Signature:** Every twin: `class GatewayXModel implements XModelV4` with `readonly specificationVersion = 'v4'` + WORKFLOW statics + same 5-key config + `getUrl() => `${baseURL}/<x>-model`` + identical catch → `asGatewayError(error, await parseAuthMethod(resolvedHeaders ?? {}))`.
**Data Shape:** Per-modality constants live as class fields: embedding declares `maxEmbeddingsPerCall = 2048; supportsParallelCalls = true` (feeds embedMany's batching scheduler). Header families mirror the language model (`ai-embedding-model-specification-version`, etc.); response schemas are typed per modality (NOT z.any()) with `.transform` renaming.

### Decisive source
```ts
export class GatewayEmbeddingModel implements EmbeddingModelV4 {
  readonly specificationVersion = 'v4';
  readonly maxEmbeddingsPerCall = 2048;
  readonly supportsParallelCalls = true;
  // …same WORKFLOW_SERIALIZE/DESERIALIZE pair, same config shape as GatewayLanguageModel
```

**Flow:** provider factory constructs each twin with the IDENTICAL config object → each twin posts to its own single endpoint (`/embedding-model`, `/image-model`, …) with its own header family → errors funnel identically.
**Invariant:** The FAMILY contract is: one endpoint per modality, identity carried in headers, error handling byte-identical, batching knobs expressed as class FIELDS not options. Porting a new modality means copying the skeleton and changing exactly: endpoint suffix, header prefix, result schema, capability fields.
**Probe:** `grep -c WORKFLOW_SERIALIZE packages/gateway/src/gateway-embedding-model.ts` → `2`. Direct tests: gateway-embedding-model.test.ts (249L) + gateway-reranking-model.test.ts 'should create GatewayRerankingModel for reranking alias' via gateway-provider.test.ts :528–586 alias assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayEmbeddingModel maxEmbeddingsPerCall supportsParallelCalls", limit: 10 });
```
Resolves in `gateway-embedding-model.ts`; provider-side factory wiring at `gateway-provider.ts 419–578`.

## Verdict
Adopt the shared skeleton for any multi-modality provider package; adapt endpoint/header names and capability fields per modality; omit nothing — the class-field batching contract is what keeps embedMany scheduling correct without per-call negotiation.
