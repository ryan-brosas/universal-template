<!-- capsule-v2 -->
# Embedding batch/parallelism scheduler — how does embedMany split a large values array across model calls without ever misaligning embeddings to inputs?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the exact chunking × parallel-batching state machine that keeps result[i] aligned with values[i] while honoring per-call limits and provider concurrency capability?

## Two-path scheduler
**Path/Symbol:** `packages/ai/src/embed/embed-many.ts:embedMany` (:49–416; split point :204, chunking :286, parallel batching :300–378).
**Signature:** `embedMany({ model, values, maxParallelCalls = Infinity, maxRetries?, abortSignal?, headers?, providerOptions?, telemetry?, onStart?, onEnd?, _internal? }): Promise<EmbedManyResult>`.
**Data Shape:** `maxEmbeddingsPerCall` and `supportsParallelCalls` are awaited off the resolved model (`Promise.all` :200–202) and may be numbers, promises, or undefined. Output: `{ values, embeddings (flat, index-aligned), usage {tokens}, warnings[], providerMetadata?, responses[] }`.

### Decisive source
```ts
if (maxEmbeddingsPerCall == null || maxEmbeddingsPerCall === Infinity) {
  // PATH A: one doEmbed call with ALL values, wrapped in retry()
  ...
}
const valueChunks = splitArray(values, maxEmbeddingsPerCall);   // :286
...
const parallelChunks = splitArray(
  valueChunks,
  supportsParallelCalls ? maxParallelCalls : 1,                  // :300-303
);
for (const parallelChunk of parallelChunks) {
  const results = await Promise.all(parallelChunk.map(chunk => retry(...doEmbed...)));
  for (const result of results) {                                 // :358-377
    embeddings.push(...result.embeddings);
    warnings.push(...result.warnings);
    responses.push(result.response);
    tokens += result.usage.tokens;
    // per-provider shallow merge of providerMetadata
```

**Flow:** resolve model → prepare retries → await `[maxEmbeddingsPerCall, supportsParallelCalls]` → if limit null/Infinity: single retry-wrapped doEmbed(values) → else splitArray into value chunks → group chunks into parallel batches (`supportsParallelCalls ? maxParallelCalls : 1`) → per batch `Promise.all` of retry-wrapped doEmbeds → sequential accumulation in batch order → logWarnings once → onEnd → DefaultEmbedManyResult.
**Invariant:** embeddings are reassembled by PUSH ORDER, never by index arithmetic: chunks are produced in input order, batches execute in order, and within a batch `Promise.all` preserves array position — so `embeddings[i]` corresponds to `values[i]` even when calls complete out of order. Usage sums across calls; warnings concatenate; `providerMetadata` merges per-provider-key with spread (`{...(prev ?? {}), ...metadata}` :363–375) so later chunks overwrite only colliding keys.
**Probe:** `packages/ai/src/embed/embed-many.test.ts` (:39–86 resolvable-gated ordering tests pin all three schedules: false→strict interleave `start-0,end-0,start-1,...`, true→all starts first `start-0,start-1,start-2,end-*`, maxParallelCalls=2→two-at-a-time; :289–321 two-chunk usage sum asserts `{tokens:30}`).

## Capability semantics (what a porter gets wrong)
**Path/Symbol:** `packages/provider/src/embedding-model/v4/embedding-model-v4.ts:maxEmbeddingsPerCall/supportsParallelCalls` (:31–48).
**Data Shape:** `maxEmbeddingsPerCall: number | PromiseLike<number | undefined> | undefined` — `Infinity` means "no limit"; `undefined` behaves like no-limit too (both take PATH A). `supportsParallelCalls: boolean | PromiseLike<boolean>` gates ONLY concurrency, not correctness.

### Decisive source
```ts
/**
 * Limit of how many embeddings can be generated in a single API call.
 * Use Infinity for models that do not have a limit.
 */
readonly maxEmbeddingsPerCall:
  | PromiseLike<number | undefined>
  | number
  | undefined;
```

**Flow:** a provider adapter declares both capabilities up-front; the scheduler trusts them blindly — it never probes the API or validates returned embedding counts against chunk size.
**Invariant:** `supportsParallelCalls:false` forces batch width 1 but still uses the CHUNKED path when a finite limit exists; porters who treat `false` as "single call with everything" break models whose API rejects oversized batches. Both capability fields are awaited lazily per call (:200–202), so middleware/providers may compute them async.
**Probe:** `packages/ai/src/embed/embed-many.test.ts:137` ('should support maxParallelCalls' pins width-2 scheduling via event order).

## Retry granularity + NaN usage sentinel
**Path/Symbol:** `packages/ai/src/embed/embed-many.ts:retry(async () => ...)` per chunk (:308, :206) ; usage default :229/:331.
**Data Shape:** missing provider usage becomes `{ tokens: NaN }`, NOT `{tokens: 0}`.

### Decisive source
```ts
const usage = modelResponse.usage ?? { tokens: NaN };
```

**Flow:** each chunk (or the single call) carries its OWN retry loop — a transient failure in chunk k retries only chunk k, preserving completed siblings. Abort signal passes through untouched to every doEmbed.
**Invariant:** NaN propagates through summation (`tokens += result.usage.tokens`), so one provider omitting usage poisons the total to NaN BY DESIGN rather than silently under-reporting cost. Porters who default to 0 hide billing errors; porters who throw lose partial-result semantics.
**Probe:** `packages/ai/src/embed/embed.test.ts:79` describe 'result.usage' + `packages/ai/src/embed/embed-many.ts:229` byte-exact `grep -n 'usage ?? { tokens: NaN }' packages/ai/src/embed/embed-many.ts` → 2 hits (:229, :331).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "embedMany values splitArray maxEmbeddingsPerCall", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-path scheduler, push-order reassembly invariant, per-chunk retry granularity, and the NaN usage sentinel verbatim — they encode provider-API economics (batch limits, rate-limited concurrency) not host specifics. Adapt `splitArray` (trivially portable: throws on chunkSize<=0, slices forward). Omit the telemetry dispatcher/callback plumbing if your host has its own observability bus — see swallowing-callback-bus.md for the contract being replaced. Direct tests exist for all three schedules and usage aggregation; runner unavailable in this environment (no node_modules) — behavior pinned by reading test assertions, not executing them.
