<!-- capsule-v2 -->
# Session model resolution — how do you resolve a session's pinned model/variant into a provider-native request route without leaking credentials?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A session pins a provider/model/variant triple; the runner needs a concrete provider-native request route with auth attached — but credentials arrive from three places (stored credential, catalog apiKey, catalog api settings) and provider APIs differ. How do you order selection, variant overlay, credential precedence, and route mapping so unsupported combos fail loudly and secrets never reach provider JSON?

## Four-stage resolution pipeline
**Path/Symbol:** `packages/core/src/session/runner/model.ts` (`locationLayer.resolve` :182-216, `withVariant` :104-126, `apiKey` :83-88, `withDefaults` :90-102, `fromCatalogModel` :131-170, `supported` :175-177).
**Signature:** `resolve(session: SessionSchema.Info) → Effect<Model, ModelNotSelectedError | ModelUnavailableError | VariantUnavailableError | UnsupportedApiError | Integration.AuthorizationError>`; `fromCatalogModel(model, credential?) → Effect<Model, UnsupportedApiError>`.
**Data Shape:** `ModelV2.Info` carries `request.{headers,body}`, `api.{type,package,url,id,settings}`, `variants[]`, `limit.{context,output}`; the output `Model` binds a route (id, endpoint.baseURL, defaults.headers/http.body/limits, auth) to an api-level model id.

### Decisive source
```ts
// model.ts:131-170 (abridged) — three-route mapping + fail-loud unsupported
if (resolved.api.type === "aisdk" && resolved.api.package === "@ai-sdk/openai") {
  return Effect.succeed(
    withDefaults(resolved, OpenAIResponses.route)
      .with({ auth: key === undefined ? Auth.none : Auth.bearer(key) })
      .model({ id: resolved.api.id }),
  )
}
...
return Effect.fail(
  new UnsupportedApiError({ providerID: resolved.providerID, modelID: resolved.id, api: apiName(resolved) }),
)
```

**Flow:** (1) SELECTION — session.model pin wins; otherwise catalog default if `supported()`, else first supported from `catalog.model.available()`; pinned-but-unavailable → ModelUnavailableError, nothing selected → ModelNotSelectedError. (2) VARIANT — session.model.variant ("default"/undefined defers to the catalog's own request.variant) finds the variant in model.variants; an explicit unknown variant FAILS (VariantUnavailableError) while a catalog-default missing variant passes through; the overlay is an immer produce merging variant headers/body OVER the catalog request. (3) CREDENTIAL — key credentials with metadata project the metadata INTO the request body (tenant-style fields) and their key becomes the auth value; OAuth credentials use the access token only, metadata NEVER projected; stored credentials beat catalog-configured apiKey, and withDefaults STRIPS the apiKey property from the http body so secrets never reach provider JSON. (4) ROUTE — exactly three native routes: @ai-sdk/openai → OpenAIResponses.route (bearer), @ai-sdk/anthropic → AnthropicMessages.route (x-api-key header), @ai-sdk/openai-compatible WITH url → OpenAICompatibleChat.route (bearer); anything else (including "native" api type and url-less openai-compatible) → UnsupportedApiError with apiName like "aisdk:@ai-sdk/google". supported() mirrors the same predicate for selection-time filtering, so unsupported models are filtered BEFORE selection rather than failing mid-resolve.
**Invariant:** credential precedence is stored > catalog apiKey > api settings; the catalog apiKey never appears in the provider request body; unsupported api shapes fail loudly at resolve time (never a silently wrong route); variant failure is strict for session-pinned variants, lenient for catalog defaults.
**Probe:** `packages/core/test/session-runner-model.test.ts` (347L, 13 `it.effect`): "keeps catalog apiKey credentials out of provider JSON" pins the apiKey strip (JSON.stringify not containing the secret); "prefers stored credentials over configured auth" pins stored-key precedence + metadata body projection; "does not project OAuth account metadata into the request body" pins the OAuth metadata rule; "rejects an explicit unavailable Session variant" pins VariantUnavailableError; "rejects catalog APIs without a native route" pins UnsupportedApiError with the "aisdk:@ai-sdk/google" apiName; "reports whether a catalog model has a supported native route" pins the supported() predicate. Source pin:
```bash
grep -c 'UnsupportedApiError' packages/core/src/session/runner/model.ts   # expect 5
grep -c 'produce(' packages/core/src/session/runner/model.ts              # expect 2
grep -c 'layerWith' packages/core/src/session/runner/model.ts             # expect 1
grep -n 'promptCacheKey' packages/core/src/session/runner/llm.ts          # :204/:214
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionRunnerModel resolve fromCatalogModel withVariant UnsupportedApiError Auth bearer catalog model variant", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-stage pipeline (selection → variant overlay → credential merge → route mapping) with the strict/lenient variant split and the fail-loud UnsupportedApiError; adopt the apiKey-strip and metadata-projection rules as the credential contract. Adapt the three route mappings to your provider SDKs; layerWith() is the test/embedding seam to copy for direct resolve injection. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
