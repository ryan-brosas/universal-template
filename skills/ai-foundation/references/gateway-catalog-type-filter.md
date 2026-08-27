<!-- capsule-v2 -->
# Gateway model catalog filter — why does the config endpoint silently DROP unknown modelType entries at the zod layer?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the client tolerate gateway servers that advertise newer model modalities than this SDK knows?

## Parse-then-filter inside the response schema
**Path/Symbol:** `packages/gateway/src/gateway-fetch-metadata.ts:gatewayAvailableModelsResponseSchema` (85–131) + `gateway-model-entry.ts:KNOWN_MODEL_TYPES` (3–12).
**Signature:** `z.array(entry).transform(models => models.filter((m): m is … => m.modelType == null || KNOWN_MODEL_TYPES.includes(m.modelType as KnownModelType)))`.
**Data Shape:** Entry = `{id, name, description?, pricing? (renamed to cachedInputTokens/cacheCreationInputTokens), specification {specificationVersion: literal 'v4', provider, modelId}, modelType?}`. Filter keeps `modelType == null` (legacy servers predating the field) OR values in the 8-member known set: embedding, image, language, realtime, reranking, speech, transcription, video.

### Decisive source
```ts
.transform(models =>
  models.filter(
    (m): m is typeof m & { modelType?: KnownModelType | null } =>
      m.modelType == null ||
      KNOWN_MODEL_TYPES.includes(m.modelType as KnownModelType),
  ),
)
```

**Flow:** GET `{baseURL}/config` → schema parses each entry (pricing rename via nested `.transform`) → array-level transform filters unknown types → consumers (`getAvailableModels`) never see a type they can't construct.
**Invariant:** Unknown-typed models are dropped SILENTLY at parse time — this is forward compatibility by subtraction, not an error. The `nullish` acceptance for legacy servers must be kept or old gateways return empty catalogs. Pricing fields are strings on the wire (decimal-string costs) and stay strings in the parsed shape.
**Probe:** `grep -cF 'KNOWN_MODEL_TYPES.includes(m.modelType as KnownModelType)' packages/gateway/src/gateway-fetch-metadata.ts` → `1`; direct tests: gateway-fetch-metadata.test.ts 'should filter out models with unknown modelType values' (:201), 'should preserve all known modelType values' (:225), 'should accept top-level modelType when present' (:183).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "KNOWN_MODEL_TYPES GatewayLanguageModelEntry modelType filter", limit: 10 });
```
Resolves line-exact anchors in `gateway-fetch-metadata.ts` + `gateway-model-entry.ts` (entry interface :16–66).

## Verdict
Adopt parse-layer filtering for versioned catalogs shared between mismatched deployments; adapt the known-type list to your modality set; omit nothing — dropping the legacy-null branch breaks rolling upgrades.
