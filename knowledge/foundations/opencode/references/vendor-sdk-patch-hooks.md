<!-- capsule-v2 -->
# Vendor SDK patch hooks — how does a vendor plugin turn a catalog row into a live SDK instance without hardcoding vendor logic into core?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A model catalog holds declarative rows (provider api package, model ids, request headers/body), but actually calling a model needs a live SDK object constructed with vendor-specific options. How do you keep that vendor logic pluggable while core stays vendor-agnostic?

## Three-hook shape over a mutable host adapter
**Path/Symbol:** `packages/core/src/plugin/host.ts` (`mutable` :18, `aisdk.sdk` hook :44-56, `aisdk.language` hook :57-69, `catalog.transform` :71-95, `integration.method.update` :131-181), `packages/core/src/plugin/provider/openai.ts` (`OpenAIPlugin.effect` :141-165), `packages/core/src/plugin/provider/google-vertex.ts` (`GoogleVertexPlugin.effect` :60-101), `packages/core/src/plugin/provider/amazon-bedrock.ts` (`AmazonBedrockPlugin.effect` :56-91).
**Signature:** plugin hooks: `ctx.catalog.transform((evt) => Effect<void>)`, `ctx.aisdk.sdk((evt: {model, package, options, sdk}) => void|Effect)`, `ctx.aisdk.language((evt: {model, sdk, options, language}) => void|Effect)`; host converts string IDs to branded IDs and punches `DeepMutable` so plugins edit frozen rows.
**Data Shape:** catalog row: `provider{api: {type:"aisdk", package, url?}|{type:"native",...}, request:{headers, body}}`; SDK event output `{model, package, options, sdk}`; language event output `{model, sdk, options, language}`.

### Decisive source
```ts
// plugin/host.ts:44-56 — the mutable-output copy-back that makes plain callbacks work
sdk: (callback) =>
  aisdk.hook.sdk((event) => {
    const output = {
      model: mutable(event.model),
      package: event.package,
      options: event.options,
      sdk: event.sdk,
    }
    const result = callback(output)
    return Effect.suspend(() => (Effect.isEffect(result) ? result : Effect.void)).pipe(
      Effect.tap(() => Effect.sync(() => (event.sdk = output.sdk))),
    )
  }),
```

**Flow:** Every vendor plugin follows the SAME three-hook shape. (1) `catalog.transform` rewrites declarative rows: openai.ts disables `gpt-5-chat-latest` for @ai-sdk/openai providers only (chat-completions-only model while the plugin routes through Responses); google-vertex.ts resolves project/location from options→env ladders and expands `${GOOGLE_VERTEX_ENDPOINT}`/`${GOOGLE_VERTEX_PROJECT}`/`${GOOGLE_VERTEX_LOCATION}` templates in the stored api.url; amazon-bedrock.ts moves a configured `endpoint` body field into `provider.api.url` once (VPC endpoint support). (2) `aisdk.sdk` constructs the live SDK: guarded by `evt.package` equality (or inclusion for subpackages), dynamically imports the vendor SDK, merges resolved options, and ASSIGNS `evt.sdk`. (3) `aisdk.language` selects the language model from the SDK: openai always `sdk.responses(api.id)`; vertex `sdk.languageModel(api.id.trim())`; bedrock `sdk.languageModel(resolveModelID(api.id, region))` with the cross-region prefix matrix, or `selectMantleModel` for the mantle subpackage. The host adapter is what makes this safe: callbacks receive a mutable output object whose fields are copied BACK onto the internal event after the callback (`Effect.tap`), so a plain function can "return" a value by assignment; `mutable()` casts rows to `DeepMutable` so plugins can edit otherwise-frozen catalog rows; string IDs are re-branded at the boundary. Plugin ORDER in State.batch determines which patch wins when two plugins touch the same row (later update lands on top).
**Invariant:** core never imports a vendor SDK; every vendor behavior is reachable only through the three hooks; `evt.package` guards are exact (subpackage inclusion is explicit, e.g. `["@ai-sdk/amazon-bedrock", "@ai-sdk/amazon-bedrock/mantle"].includes`); language selection is total per provider (a providerID guard plus a fallback assignment); the mutable output copy-back means a callback that never assigns leaves the event unchanged.
**Probe:** `packages/core/test/plugin/provider-openai.test.ts` (176L, 7 `it.effect`): "uses the Responses API for language models" pins `calls == ["responses:gpt-5"]`; "disables gpt-5-chat-latest during catalog transforms" + "does not disable gpt-5-chat-latest for non-OpenAI providers" pin the scoped disable. `packages/core/test/plugin/provider-google-vertex.test.ts` (387L, 9 `it.effect`): pins env precedence, template expansion to regional endpoints, global endpoint, us-central1 default, and the auth-fetch wrap only for openai-compatible endpoints. `packages/core/test/plugin/provider-amazon-bedrock.test.ts` (622L, 17 `it.effect`): pins the 30-case cross-region prefix matrix, endpoint→baseURL move, bearer-token env write-back, and the default credential chain. Source pin:
```bash
grep -c 'gpt-5-chat-latest' packages/core/src/plugin/provider/openai.ts        # expect 2
grep -c 'authFetch'           packages/core/src/plugin/provider/google-vertex.ts # expect 3
grep -c 'resolveModelID'      packages/core/src/plugin/provider/amazon-bedrock.ts # expect 2
grep -c 'Effect.tap'          packages/core/src/plugin/host.ts                 # expect 2
grep -c 'it.effect'           packages/core/test/plugin/provider-amazon-bedrock.test.ts # expect 17
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "OpenAIPlugin aisdk sdk language hook catalog transform gpt-5-chat-latest GoogleVertexPlugin replaceVertexVars AmazonBedrockPlugin resolveModelID PluginHost mutable DeepMutable copy-back", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-hook plugin shape (catalog rewrite → SDK construction → language selection), the mutable-output copy-back adapter, exact-package guards, and dynamic SDK import inside the hook. Adapt the event shapes and the catalog row schema to the host. Omit the specific vendor heuristics (chat-latest disable, Vertex templates, Bedrock prefix matrix) — they are site-specific, but keep their STRUCTURE: declarative row rewrite first, SDK construction second, model selection third. Coverage caveat: the 33 remaining vendor bodies share this shape but only a subset have direct tests (provider-*.test.ts exist per vendor); the host copy-back is pinned indirectly through every vendor test; Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
