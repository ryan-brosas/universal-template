<!-- capsule-v2 -->
# Gateway batch API — how do durable multi-request batches stay replay-safe and abort-honest?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What are the three batch endpoints' contracts, where must the idempotency key ride, and why do aborts bypass gateway-error wrapping?

## Batch start/status/results trio
**Path/Symbol:** `packages/gateway/src/gateway-language-model-batch.ts:GatewayBatchLanguageModel` (Class :41–253) — `experimental_doStartBatch` (:61–124), `experimental_doGetBatchStatus` (:126–170), `experimental_doGetBatchResults` (:172–236).
**Signature:** `doStartBatch({requests, providerOptions, headers, abortSignal}) => {batchId, status…, warnings}`; `doGetBatchResults(batchId) => ReadableStream<BatchV4ItemResult>` (NDJSON); endpoints `POST {baseURL}/batch/{start|status|results}`.
**Data Shape:** `batchId` is the GATEWAY job id — provider-native ids never leave the server; results stream is one JSON object per line validated minimally as `{id: string, status: 'cancelled'|'expired'|'failed'|'succeeded'}` + catchall.

### Decisive source
```ts
const idempotencyKey = getGatewayBatchIdempotencyKey(providerOptions);
const forwardedProviderOptions = omitGatewayIdempotencyKey(providerOptions);
headers: combineHeaders(resolvedHeaders, headers, this.getBatchConfigHeaders(),
  await resolve(this.config.o11yHeaders),
  idempotencyKey != null ? {'idempotency-key': idempotencyKey} : undefined),
body: { modelId, requests: requests.map(r => ({id: r.id,
  options: this.maybeEncodeFileParts(r.options)})),
  ...(forwardedProviderOptions != null && {providerOptions: forwardedProviderOptions}) },
...
catch (error) {
  if (isAbortOrTimeoutError(error)) throw error;  // preserve cancellation
  throw await asGatewayError(error, await parseAuthMethod(resolvedHeaders ?? {}));
}
```
The header/body split is load-bearing: the Gateway hashes the RAW BODY for replay payload identity but normalizes the idempotency-key HEADER separately — leaving `gateway.idempotencyKey` inside the forwarded body would make equivalent retries produce different digests (false 422).

**Flow:** start → status (same error funnel; 400 while non-terminal is a failedResponseHandler case for results) → results NDJSON parsed by an incremental line splitter (`parseGatewayBatchResultLines` :398–441: buffers partial lines across chunks, flushes trailing unterminated line, skips blanks, cancels reader on early exit) that also converts ISO `response.timestamp` strings to Date objects for succeeded items.
**Invariant:** Abort/TimeoutError must NEVER become retryable Gateway 500s — an aborted start may already be accepted server-side, so cancellation propagates raw (`isAbortOrTimeoutError` checks name on Error OR DOMException since DOMException doesn't extend Error). Status `requestCounts` forwards ONLY when all four counters are numeric (never fabricate zeros). Every request carries `ai-model-id` config header.
**Probe:** deterministic probes: `grep -c "isAbortOrTimeoutError(error)" packages/gateway/src/gateway-language-model-batch.ts` → `3`; `grep -c "'idempotency-key': idempotencyKey" …ts` → `1`. Direct tests: `gateway-language-model-batch.test.ts` (604 lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayBatchLanguageModel experimental_doStartBatch", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 :61-124; anthropic/openai batch twins at lower rank
```

## Verdict
Adopt the three-endpoint shape, header-not-body idempotency transport, abort passthrough ladder, and all-or-nothing counts rule; adapt endpoint paths and wire fields; note provider-side twins (anthropic-messages-batch / openai-responses-batch) implement the SAME spec surface per provider.
