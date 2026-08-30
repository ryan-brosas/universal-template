<!-- capsule-v2 -->
# Bedrock model dispatch — how does one embedder speak four different Bedrock embedding APIs?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How are request/response shapes selected per Bedrock model family?

## startsWith-family dispatch on BOTH sides of the call
**Path/Symbol:** `src/services/code-index/embedders/bedrock.ts:_invokeEmbeddingModel` (:176-266).
**Signature:** `private async _invokeEmbeddingModel(text: string, model: string): Promise<{embedding: number[]; inputTextTokenCount?: number}>`.
**Data Shape:** four families — `amazon.nova-2-multimodal*` (taskType SINGLE_EMBEDDING, embeddingPurpose GENERIC_INDEX, embeddingDimension 1024), `amazon.titan-embed*` (`{inputText}` → `{embedding, inputTextTokenCount}`), `cohere.embed-v4*` (`{texts:[t], input_type:"search_document", embedding_types:["float"]}` → `{embeddings:{float:[[...]]}}`), `cohere.embed*` v3 (`{texts:[t], input_type:"search_document"}` → `{embeddings:[[...]]}`). Unknown models DEFAULT to Titan format.

### Decisive source
```ts
} else if (model.startsWith("cohere.embed-v4")) {
  requestBody = { texts: [text], input_type: "search_document", embedding_types: ["float"] }
}
// response side mirrors request side per family:
return { embedding: responseBody.embeddings?.float?.[0] || responseBody.embeddings?.[0] }
```

**Flow:** dispatch happens TWICE — once to build the InvokeModel body, once to parse the response; the two ladders must stay in lockstep. Retry-on-429 is `ThrottlingException` here (not HTTP status). Validation maps AWS error NAMES (UnrecognizedClient/AccessDenied/ResourceNotFound) to typed messages. Credentials: `fromIni({profile})` when set else `fromNodeProviderChain()`.
**Invariant:** adding a family means touching BOTH ladders + keeping `input_type: "search_document"` for indexing-time Cohere calls (query-time would be `search_query`, not used here because queries go through the same indexer-side path with prefix handling elsewhere).
**Probe:** `src/services/code-index/embedders/__tests__/bedrock.spec.ts`; executed pins: taskType literal, search_document count=2 (v3+v4).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "BedrockEmbedder _invokeEmbeddingModel InvokeModelCommand nova titan cohere", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt paired request/response dispatch tables keyed by model-prefix families. Adapt family list as AWS ships models. Omit IAM plumbing.
