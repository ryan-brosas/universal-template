<!-- capsule-v2 -->
# Provider retry ladder — which provider errors auto-retry, what delay applies, and when must a server-suggested delay abort the request instead of waiting?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** reproduce OpenAI/Anthropic SDK retry semantics while making the backoff sleep interruptible by the caller’s AbortSignal.

## SDK-parity retry with abortable sleep
**Path/Symbol:** `packages/ai/src/utils/provider-retry.ts:retryProviderRequest` (105-125); helpers `isRetryableProviderError` (23-35), `validateServerRetryDelayMs` (37-49), `getRetryDelayMs` (51-67), `abortableSleep` (75-95), `isProviderError` guard (14-20).
**Signature:** `export async function retryProviderRequest<T>(request: () => Promise<T>, options?: { maxRetries?: number; maxRetryDelayMs?: number; signal?: AbortSignal }): Promise<T>`.
**Data Shape:** `ProviderError = Error & { status?: number; headers?: Headers }` (duck-typed via isProviderError). Defaults: maxRetries 0 (!), maxRetryDelayMs 60_000.

### Decisive source
```ts
function isRetryableProviderError(error: ProviderError): boolean {
	const shouldRetry = error.headers?.get("x-should-retry");
	if (shouldRetry === "true") return true;
	if (shouldRetry === "false") return false;
	if (error.status === undefined) return true;
	return (error.status === 408 || error.status === 409 || error.status === 429 ||
		(typeof error.status === "number" && error.status >= 500));
}
function getRetryDelayMs(error: ProviderError, retryIndex: number, maxRetryDelayMs?: number): number {
	// retry-after-ms header -> retry-after (seconds or HTTP-date) both pass through
	// validateServerRetryDelayMs, which THROWS when delay > max:
	const exponentialDelay = Math.min(0.5 * 2 ** retryIndex, 8) * 1000;
	return exponentialDelay * (1 - Math.random() * 0.25);
}
for (;;) {
	try { return await request(); }
	catch (error) {
		if (options.signal?.aborted) throw createAbortError();
		if (retriesRemaining <= 0 || !isProviderError(error) || !isRetryableProviderError(error)) throw error;
		const retryIndex = maxRetries - retriesRemaining;
		retriesRemaining--;
		await abortableSleep(getRetryDelayMs(error, retryIndex, options.maxRetryDelayMs), options.signal);
	}
}
```

**Flow:** attempt → catch → if signal already aborted throw AbortError → non-ProviderError or non-retryable rethrow → compute delay (`x-should-retry` header vetoes first: `"true"` forces retry even off-list, `"false"` vetoes everything; then no-status ⇒ retry; then 408/409/429/5xx) → sleep abortably → call `request()` again as a FRESH request.
**Invariant:** each retry invokes `request()` anew so SDK retry-count headers stay zero — callers must pass the SDK `maxRetries: 0`. A server-requested delay above `maxRetryDelayMs` THROWS immediately (never silently waits); set maxRetryDelayMs to 0 to disable the limit. The abort signal is checked before every sleep and every retry, and aborts interrupt mid-sleep.
**Probe:** `packages/ai/test/provider-retry.test.ts` — EXECUTED 2026-08-25, vitest reports 5/5 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "retryProviderRequest", file_pattern: "packages/ai/src/utils/provider-retry.ts" });
```

## Verdict
Adopt the whole ladder verbatim: header veto, status list, jittered exponential cap at 8s base 0.5s, throw-on-oversized-server-delay, fresh-request retries, signal-checked sleeps. Adapt only the ProviderError duck-type to your HTTP client’s error shape. Omit nothing silently — dropping the validateServerRetryDelayMs throw reintroduces an unbounded stall the source explicitly refuses.
