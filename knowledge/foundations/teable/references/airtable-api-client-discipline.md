<!-- capsule-v2 -->
# Airtable API client discipline — what rate, retry, and timeout policy keeps a 5 req/s source API happy for hours?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the official-API client throttle, classify errors, and time out so a long import neither trips 429s nor hangs on dead connections?

## Throttled fetch with stall-based timeouts
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-api.client.ts`:`AirtableApiClient.request` (:110–171).
**Signature:** `private async request<T>(path: string): Promise<T>`; constructor takes `getAccessToken: IAirtableAccessTokenProvider` (per-request token provider).
**Data Shape:** `AirtableApiError {status, type?}`; typed subclass `AirtableIteratorExpiredError` (422 `LIST_RECORDS_ITERATOR_NOT_AVAILABLE`); constants: `minRequestIntervalMs = 220` (stay under Airtable's 5 req/s per base), `rateLimitWaitMs = 30_000` (documented penalty), `maxRetries = 3`, `recordsPageSize = 100`, `requestTimeoutMs = 30_000`.

### Decisive source
```ts
// Stall-based, not a whole-request deadline: the timer refreshes on
// every body chunk, so a slow-but-flowing large page is never killed —
// only a silently dropped connection (no headers or no data for the
// window) aborts and retries like any network error.
const controller = new AbortController();
const stallTimer = setTimeout(
  () => controller.abort(new Error(`no response data for ${requestTimeoutMs}ms`)),
  requestTimeoutMs
);
...
if (response.status === 429 && attempt < maxRetries) {
  await sleep(rateLimitWaitMs); attempt++; continue;
}
if (response.status >= 500 && attempt < maxRetries) {
  await sleep(1000 * 2 ** attempt); attempt++; continue;
}
if (response.status === 422 && errorBody.type === 'LIST_RECORDS_ITERATOR_NOT_AVAILABLE') {
  throw new AirtableIteratorExpiredError();
}
```
Body read refreshes the timer per chunk (`readBody`: `for await (const chunk of response.body) stallTimer.refresh();`).

**Flow:** per request → throttle to 220 ms spacing → fetch token FRESH each call (integration OAuth tokens refresh server-side past the ~60 min lifetime) → stall-guarded fetch + chunked body read → network/timeout ⇒ exponential backoff retry within one shared budget with 429 ⇒ fixed 30 s wait and ≥500 ⇒ exponential — all inside `maxRetries`; 422 iterator-expiry becomes a TYPED error so the caller restarts listing instead of failing.
**Invariant:** One retry budget covers rate-limit waits AND transient network errors. Timeout is inactivity-based, never a whole-request deadline. The token is resolved per request, never cached on the client.
**Probe:** `grep -cF "LIST_RECORDS_ITERATOR_NOT_AVAILABLE" apps/nestjs-backend/src/features/airtable-import/airtable-api.client.ts` returns 2; `grep -cF "returnFieldsByFieldId" ...` returns 1 (list requests always ask for ids-keyed cells).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"AirtableApiClient throttle readBody AirtableApiError","limit":5,"detail":"ids"}'
```

## Verdict
Adopt per-request token providers, spacing throttles, inactivity timeouts, and typed pagination-expiry errors for any third-party list API at scale; adapt intervals to the provider's documented limits; omit Airtable's specific 30 s penalty constant where the host targets a different API. Coverage caveat: none.
