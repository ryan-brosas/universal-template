<!-- capsule-v2 -->
# Rerank orchestrator — how do you rerank documents against a query and hydrate results back to the caller's originals without off-by-one or type loss?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What are the empty-input, document-typing, topN, and ranking→document hydration contracts a rerank port must preserve?

## Empty-documents short-circuit
**Path/Symbol:** `packages/ai/src/rerank/rerank.ts:rerank` (:38–343; guard :161–206).
**Signature:** `rerank<VALUE extends JSONObject | string>({ model, documents: VALUE[], query, topN?, maxRetries?, abortSignal?, headers?, providerOptions?, telemetry?, onStart?, onEnd? }): Promise<RerankResult<VALUE>>`.
**Data Shape:** returns `{ originalDocuments, ranking[{originalIndex, score, document}], providerMetadata?, response }` with lazy getter `rerankedDocuments`.

### Decisive source
```ts
if (documents.length === 0) {
  await notify({ event: {...startEvent fields...}, callbacks: [resolvedOnStart, ...] });
  await notify({ event: { ..., ranking: [], warnings: [], providerMetadata: undefined,
      response: { timestamp: new Date(), modelId: model.modelId } },
    callbacks: [resolvedOnEnd, ...] });
  return new DefaultRerankResult({ originalDocuments: [], ranking: [], ... });
}
```

**Flow:** empty input fires BOTH lifecycle callbacks with a synthetic `{timestamp, modelId}`-only response, then returns — BEFORE `prepareRetries`, before the tracing span, before doRerank.
**Invariant:** the short-circuit sits OUTSIDE the tracing span and retry setup, so telemetry sees start+end but no span/error path; porters who move it inside the span double-count spans for trivial calls; porters who skip the callbacks break observers that count operations.
**Probe:** `packages/ai/src/rerank/rerank.test.ts:845` ('should fire callbacks for empty documents' asserts startEvent.callId/documents=[] AND endEvent.ranking=[] byte-exact).

## Wire document typing + topN delegation
**Path/Symbol:** `packages/ai/src/rerank/rerank.ts:213–216` + `packages/provider/src/reranking-model/v4/reranking-model-v4-call-options.ts:documents/topN`.
**Data Shape:** wire shape is a discriminated union `{type:'text', values:string[]} | {type:'object', values:JSONObject[]}`; `topN?: number` is advisory.

### Decisive source
```ts
const documentsToSend: RerankingModelV4CallOptions['documents'] =
  typeof documents[0] === 'string'
    ? { type: 'text', values: documents as string[] }
    : { type: 'object', values: documents as JSONObject[] };
```

**Flow:** the union is built ONCE from the first element's runtime type (generic VALUE is erased at runtime) and passed verbatim into every doRerank attempt.
**Invariant:** (1) typing is FIRST-ELEMENT ONLY — a heterogeneous array mislabels the whole batch; porters adding per-element checks diverge from upstream wire behavior. (2) The orchestrator NEVER slices to topN: it forwards topN and returns whatever ranking arrives. A local post-slice would change result semantics for providers that ignore/clamp topN differently.
**Probe:** `packages/ai/src/rerank/rerank.test.ts:66` inline snapshot pins exact wire options (`"topN": 3`, `"type": "text"`); `grep -n 'typeof documents\[0\] === .string.' packages/ai/src/rerank/rerank.ts` → single hit :214.

## Ranking hydration by trusted index
**Path/Symbol:** `packages/ai/src/rerank/rerank.ts:301–307 & 323–327` + `packages/provider/src/reranking-model/v4/reranking-model-v4-result.ts:ranking`.
**Data Shape:** provider returns `ranking: Array<{index:number, relevanceScore:number}>` sorted descending by score.

### Decisive source
```ts
ranking: ranking.map(ranking => ({
  originalIndex: ranking.index,
  score: ranking.relevanceScore,
  document: documents[ranking.index],
})),
```

**Flow:** each provider index is mapped through the CALLER'S ORIGINAL array — `originalIndex` is preserved alongside so callers can join back without trusting order.
**Invariant:** the orchestrator does NOT validate that index ∈ [0, documents.length); an out-of-range index yields `undefined` document silently. Porters who re-sort by score locally are fine (already sorted), but porters who dedupe or filter rankings break the index↔document pairing contract. `response.id/timestamp/modelId/headers/body` all default individually (`response?.timestamp ?? new Date()`) so partial provider responses still produce a complete result envelope.
**Probe:** `packages/ai/src/rerank/rerank.test.ts:112` inline snapshot pins `{document:'cloudy day in the mountains', originalIndex:2, score:0.9}` ordering; `grep -n 'originalIndex: ranking.index' packages/ai/src/rerank/rerank.ts` → single hit :324.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "rerank documents ranking relevanceScore", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the empty-input callback contract, first-element wire discrimination, topN delegation, and trusted-index hydration verbatim — they define the cross-provider rerank wire protocol. Adapt the DefaultRerankResult class (plain object + getter suffices in other hosts). Omit nothing behavioral; the file is small enough to port whole. Direct tests exist for string docs, object docs, callbacks, and the empty case; runner unavailable here (no node_modules) — assertions pinned by reading, not executing.
