<!-- capsule-v2 -->
# Embedder batching kernel — how do 8 providers share one token-budget batching loop?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How are texts split into API batches, and what happens to oversized items?

## chars/4 estimation, greedy fill, drop-don't-fail oversize
**Path/Symbol:** `src/services/code-index/embedders/{openai.ts,openai-compatible.ts,openrouter.ts,bedrock.ts}:createEmbeddings` (identical loop; openai :80-121).
**Signature:** `createEmbeddings(texts: string[], model?: string): Promise<EmbeddingResponse>`; constants `MAX_BATCH_TOKENS=100000`, `MAX_ITEM_TOKENS=8191` (Gemini overrides to 2048 via constructor param).
**Data Shape:** `remainingTexts` worklist mutated by reverse-order splices so indices stay valid while removing processed items.

### Decisive source
```ts
const itemTokens = Math.ceil(text.length / 4)
if (itemTokens > this.maxItemTokens) { console.warn(...); processedIndices.push(i); continue } // DROPPED
if (currentBatchTokens + itemTokens <= MAX_BATCH_TOKENS) { currentBatch.push(text); ... } else break
```

**Flow:** optional model-specific query prefix first (double-prefix guard `text.startsWith(queryPrefix)`; prefix that would push past the item cap is silently NOT added) → greedy fill until the batch budget would overflow → embed → repeat. Oversized items are warned-and-DROPPED (they produce no embedding and no error). Bedrock's `_embedBatchWithRetries` loops per-text InvokeModel because Titan/Cohere don't batch.
**Invariant:** embeddings array order matches input order ONLY among non-dropped texts — a port must keep its own index mapping if it needs positional fidelity for dropped items. The /4 heuristic deliberately over-estimates CJK and under-estimates whitespace-heavy code; it is a guard, not accounting.
**Probe:** `src/services/code-index/embedders/__tests__/openai-compatible-rate-limit.spec.ts` + `openai.spec.ts`; executed pins: MAX_ITEM_TOKENS warn-drop branches ×3 files, prefix double-guard greps.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "createEmbeddings remainingTexts MAX_BATCH_TOKENS itemTokens", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt one kernel shared across providers with provider-injected caps (the Gemini 2048 override is the pattern). Adapt the estimator to a real tokenizer if billing matters. Omit provider SDK details. Caveat: dropped-item behavior has no dedicated spec — source-read verified.
