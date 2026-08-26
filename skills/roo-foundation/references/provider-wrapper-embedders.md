<!-- capsule-v2 -->
# Provider wrapper embedders — how do Gemini/Mistral/Vercel reuse one OpenAI-compatible client?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What does each thin provider wrapper actually own, and where do silent behavior changes hide?

## Composition over the compatible embedder, plus a silent model migration
**Path/Symbol:** `src/services/code-index/embedders/{gemini.ts,mistral.ts,vercel-ai-gateway.ts}` (gemini :16-93; mistral :13-71; vercel :22-80).
**Signature:** each holds ONE `OpenAICompatibleEmbedder` built from (BASE_URL, apiKey, modelId, maxItemTokens?) and delegates both `createEmbeddings` and `validateConfiguration`.
**Data Shape:** gemini passes `GEMINI_MAX_ITEM_TOKENS=2048` (constants) — NOT the 8191 default; mistral/vercel pass MAX_ITEM_TOKENS.

### Decisive source
```ts
private static readonly DEPRECATED_MODEL_MIGRATIONS: Record<string, string> = {
  "text-embedding-004": "gemini-embedding-001",
}
private static migrateModelId(modelId: string): string {
  return GeminiEmbedder.DEPRECATED_MODEL_MIGRATIONS[modelId] ?? modelId
}
```

**Flow:** constructor validates apiKey loudly → optional migration → compose. The embedding-model registry (`src/shared/embeddingModels.ts`) is the third leg: per-provider profiles give `{dimension, scoreThreshold, queryPrefix?}` — dimension feeds collection creation, scoreThreshold becomes search minScore when the user sets none, and ONLY `nomic-embed-code` (ollama + openai-compatible profiles) carries `queryPrefix: "Represent this query for searching relevant code: "` with a lowered threshold 0.15 vs 0.4 everywhere else.
**Invariant:** dimension/scoreThreshold/prefix are looked up PER RESOLVED MODEL — silently migrating text-embedding-004→gemini-embedding-001 keeps dimension lookups correct (both 3072); a porter who drops the migration map breaks old configs at collection-creation time, not at request time. Ollama validation matches model names three ways (exact / +`:latest` / stripped `:latest`).
**Probe:** `src/services/code-index/embedders/__tests__/{gemini.spec.ts,mistral.spec.ts,vercel-ai-gateway.spec.ts,ollama.spec.ts}`; executed pins: migration table, 2048 override, 0.15-threshold count=2, prefix count=2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "EMBEDDING_MODEL_PROFILES getModelQueryPrefix migrateModelId", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt composition-based provider wrappers + a data-file model registry as the single source of dimensions/thresholds/prefixes. Adapt the registry to your product's model list. Omit deprecated-model handling if you have no legacy installs.
