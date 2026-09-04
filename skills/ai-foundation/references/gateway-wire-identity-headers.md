<!-- capsule-v2 -->
# Gateway wire identity via headers — why do all language models POST to one endpoint, and what breaks if you move the model id into the URL or body?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the gateway transport carry model identity and modality metadata for a single-endpoint router?

## Headers-as-routing contract
**Path/Symbol:** `packages/gateway/src/gateway-language-model.ts:GatewayLanguageModel` (33–233), key sites `getUrl` (222–224) and `getModelConfigHeaders` (226–232).
**Signature:** `async doGenerate(options: LanguageModelV4CallOptions): Promise<LanguageModelV4GenerateResult>` / `doStream(...)` — one shared private `getArgs`.
**Data Shape:** Request = `POST {baseURL}/language-model` with combined headers: resolved auth headers ⊕ caller `options.headers` ⊕ model-config headers (`ai-language-model-specification-version: 4`, `ai-language-model-id: <modelId>`, `ai-language-model-streaming: 'true'|'false'`) ⊕ o11y headers. Body = call options MINUS `abortSignal` (destructured out in `getArgs`). Response schema is `z.any()` — the gateway returns normalized stream parts/results that downstream AI SDK code validates.

### Decisive source
```ts
private getUrl() { return `${this.config.baseURL}/language-model`; }
private getModelConfigHeaders(modelId: string, streaming: boolean) {
  return {
    'ai-language-model-specification-version': '4',
    'ai-language-model-id': modelId,
    'ai-language-model-streaming': String(streaming),
  };
}
// doGenerate passes streaming=false; doStream passes true:
headers: combineHeaders(resolvedHeaders, options.headers,
  this.getModelConfigHeaders(this.modelId, false /* or true */),
  await resolve(this.config.o11yHeaders)),
```

**Flow:** getArgs strips abortSignal + base64-encodes inline file parts → postJsonToApi with 4-way header combine → success handler returns body verbatim (+ synthesized `request`/`response` envelopes); failure → `asGatewayError`.
**Invariant:** The STREAMING FLAG is a header, not a body field, and generate vs stream are the SAME endpoint differing only by that flag plus the response handler (JSON vs SSE). Model ids containing `/` and `:` need no escaping BECAUSE they ride a header value. Porters who put the model id in the URL break qualified ids; porters who move it into the body change the gateway's routing layer. `supportedUrls = { '*/*': [/.*/] }` declares every URL supported because file-part resolution happens server-side.
**Probe:** `grep -cF "'ai-language-model-id': modelId," packages/gateway/src/gateway-language-model.ts` → `1`; `grep -c 'getModelConfigHeaders(this.modelId, false)' …` → `1` and `(this.modelId, true)` → `1`. Direct tests: gateway-language-model.test.ts 'should pass headers correctly', 'should remove abortSignal from the request body', 'Image part encoding' describe ×2 (:298 doGenerate, :857 doStream).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayLanguageModel doStream maybeEncodeFileParts", limit: 10 });
```
Resolves line-exact: `maybeEncodeFileParts Method 199-220`, `doStream Method 116-192`.

## Verdict
Adopt the headers-carry-identity pattern for any multi-tenant proxy endpoint; adapt the header names to your platform's conventions; omit the `z.any()` passthrough only if your consumers lack a downstream validator. Coverage caveat: none — 1783 lines of direct tests cover both paths incl. error conversion.
