<!-- capsule-v2 -->
# Gateway provider orchestrator — how does one `createGateway()` closure serve eight model modalities plus observability endpoints without duplicating config?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How is the gateway provider factory structured so every modality factory shares one baseURL/auth/fetch/o11y wiring, and which members are aliases vs distinct factories?

## Factory closure + alias fan-out
**Path/Symbol:** `packages/gateway/src/gateway-provider.ts:createGateway` (286–638).
**Signature:** `function createGateway(options: GatewayProviderSettings = {}): GatewayProvider`.
**Data Shape:** Closure captures per-instance state (`pendingMetadata`, `metadataCache`, `lastFetchTime`, resolved `baseURL`); every model constructor receives `{ provider: 'gateway', baseURL, headers: getHeaders, fetch: options.fetch, o11yHeaders }` — `getHeaders` is passed as the FUNCTION, not awaited, so auth resolves lazily per request. `gateway` is a module-level singleton via `createGateway()` at :640.

### Decisive source
```ts
const createLanguageModel = (modelId: GatewayModelId) => {
  return new GatewayLanguageModel(modelId, {
    provider: 'gateway',
    baseURL,
    headers: getHeaders,          // function ref → lazy per-request auth
    fetch: options.fetch,
    o11yHeaders: createO11yHeaders(),
  });
};
// …identical config object for image/video/embedding/reranking/speech/transcription…
provider.chat = provider.languageModel;
provider.embedding = provider.embeddingModel;
provider.image = provider.imageModel;
provider.video = provider.videoModel;
provider.tools = gatewayTools;
```

**Flow:** `createGateway(settings)` → resolve `baseURL` once (`withoutTrailingSlash(options.baseURL) ?? 'https://ai-gateway.vercel.sh/v4/ai'`) → define `createAuthHeaders`/`getHeaders`/modality factories inside the closure → attach call-signature guard + spec version + aliased methods → return the callable provider.
**Invariant:** ALL modality factories must share the SAME `headers: getHeaders` function reference and `fetch` override — porting a per-modality snapshot of headers freezes OIDC token rotation and breaks team-scoped requests. Aliases are ASSIGNMENTS (`provider.chat = provider.languageModel`), so monkey-patching one alias mutates the canonical method.
**Probe:** `grep -c "metadataCacheRefreshMillis ?? 1000 \* 60 \* 5" packages/gateway/src/gateway-provider.ts` → `1` (default 5-min cache window lives here, not in the metadata class); direct test `packages/gateway/src/gateway-provider.test.ts` ('should use default 5 minute refresh interval when not specified') pins the same number.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createGateway", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves line-exact: `ai.packages.gateway.src.gateway-provider.createGateway Function gateway-provider.ts 286-638`.

## Verdict
Adopt the closure-per-instance shape with lazy header resolution and alias-by-assignment (it is what keeps OIDC tokens fresh across a long-lived provider); adapt the default base URL and o11y env names to your host; omit the deprecated `createGatewayProvider`/`textEmbeddingModel` export shims unless mirroring the public API surface. Coverage caveat: none — path covered `no_recorded_issue`, direct tests exist for every factory member.
