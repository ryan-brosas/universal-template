<!-- capsule-v2 -->
# fetchWithRetry — timeout-per-attempt with quadratic backoff and a status whitelist

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** Which HTTP responses deserve another attempt, and how do you keep each attempt from hanging forever?

## fetchWithRetry
**Path/Symbol:** `packages/utils/src/functions/fetch-with-retry.ts:fetchWithRetry` (1–76).
**Signature:** `fetchWithRetry(input, init?, options?: { timeout? = 5000, maxRetries? = 10, retryDelay? = 1000 }): Promise<Response>`.
**Data Shape:** resolves with the first OK `Response`; throws (a) immediately on 403 ("Unauthorized") or any other non-ok non-retryable status carrying the server's `error` message when JSON-parsable, or (b) after the final retry for network errors/timeouts/429/5xx.

### Decisive source
```ts
for (let i = 0; i < maxRetries; i++) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);   // per-attempt, not global
  try {
    const response = await fetch(input, { ...init, signal: controller.signal });
    clearTimeout(timeoutId);
    if (response.ok) return response;
    if (response.status === 429 || response.status >= 500) {         // retryable statuses
      const delay = retryDelay + Math.pow(i, 2) * 50;                // 1000,1050,1200,1450... ms
      await new Promise((r) => setTimeout(r, delay));
      continue;
    }
    if (response.status === 403) throw new Error("Unauthorized");    // permanent
    // other non-ok: parse { error } from body and throw immediately
  } catch (error) {
    clearTimeout(timeoutId);
    lastError = ...;
    if (i === maxRetries - 1)
      throw new Error(`Failed after ${maxRetries} retries. Last error: ${lastError.message}`);
    const delay = retryDelay + Math.pow(i, 2) * 50;                  // network/timeout path: same backoff
    await new Promise((r) => setTimeout(r, delay));
  }
}
```

**Flow:** every attempt gets its OWN AbortController timer — a slow response aborts that attempt but never poisons the next one; only 429 and ≥500 are retried; 403 fails fast; other non-ok statuses fail fast with the upstream error text; network exceptions share the same quadratic backoff (`retryDelay + i²·50`) as status retries.
**Invariant:** the retry budget is shared across both failure classes (statuses + network errors); the timeout is scoped per attempt via `signal`, so total wall time is bounded by `maxRetries × (timeout + max delay)`; success short-circuits without waiting.
**Probe:** no direct unit test file for fetchWithRetry. Source-grounded probe: `search_graph` resolves `fetchWithRetry`; port with your own test asserting 500 → retried with growing delays and 404 → immediate throw.
**Coverage caveat:** `packages/utils` has no test dir; the sibling util `processInBatches` IS tested in `apps/web/tests/misc/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "fetchWithRetry AbortController quadratic", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-attempt abort timeouts, the 429/5xx-only retry whitelist, fast-fail on 403/other statuses with body-derived messages, and the shared quadratic backoff; adapt defaults, the auth-status interpretation, and error-shape parsing to host. Omit response-body buffering strategies. Caveat: no direct upstream test for this seam.
