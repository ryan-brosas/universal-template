<!-- capsule-v2 -->
# Bounded web fetch — how do you cap response size, classify abort vs timeout, and refuse cross-origin redirects?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the defensive fetch contract for calling an HTTP backend from an agent tool?

## Bounded fetch
**Path/Symbol:** `src/websearch.ts:readBoundedResponse` (:192-231), signal assembly :257-259, origin check :291-297, status taxonomy :298-310; caps `MAX_RESPONSE_BYTES=256KB`, `MAX_QUERY_BYTES=8KB`, `MAX_TEXT_SOURCES=10` (:16-18).
**Signature:** `readBoundedResponse(response: Response): Promise<string>`; `validateSearchQuery(query): string`.
**Data Shape:** Typed error taxonomy: `authentication_required|authentication_failed|invalid_query|request_failed|request_timeout|request_aborted|response_too_large|invalid_response`.

### Decisive source
```ts
const declared = response.headers.get("content-length");
if (declared && /^\d+$/.test(declared) && Number(declared) > MAX_RESPONSE_BYTES) {
  await response.body?.cancel().catch(() => undefined);
  throw new WebSearchError("response_too_large", ...);
}
...
size += item.value.byteLength;
if (size > MAX_RESPONSE_BYTES) { await reader.cancel().catch(() => undefined); throw ...; }
chunks.push(item.value);

// request classification:
if (error instanceof WebSearchError) throw error;
if (baseSignal?.aborted)      throw new WebSearchError("request_aborted", ...);
if (timeoutSignal.aborted)    throw new WebSearchError("request_timeout", ...);
throw new WebSearchError("request_failed", ...sanitizeDiagnosticError(...));

// redirect defense:
if (new URL(response.url).origin !== new URL(CODEX_SEARCH_URL).origin)
  throw new WebSearchError("request_failed", "...unexpected origin.");
```
Query validation trims, refuses empty, enforces UTF-8 byte cap via TextEncoder (:98-108). Fetch options harden: `redirect:"error", credentials:"omit", cache:"no-store", referrerPolicy:"no-referrer"` (:271-274). Result parsing drops non-`text_result` rows and non-http(s) URLs silently (:181-188).

**Flow:** validate query → merge request+timeout signals → authed POST → classify failures (typed precedence: existing error > base-abort > timeout > generic) → origin pin → declared-length gate → streamed byte-count gate → JSON parse with strict shape checks.
**Invariant:** BOTH size gates cancel the body (never read past the cap into memory); abort-vs-timeout attribution compares the RIGHT signal; upstream error text is redacted through `sanitizeDiagnosticError` before embedding in messages (test-pinned: no token/account-id leakage); citations are protocol-safe (http/https only).
**Probe:** `tests/websearch.test.ts` (:150 query validation, :385 declared content-length over-cap rejects, next test streamed no-content-length over-cap rejects, :282/:378-382 auth-failure message redaction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "readBoundedResponse MAX_RESPONSE_BYTES parseSearchResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual size gates + typed failure precedence + origin pinning wholesale. Adapt endpoint/caps/error vocabulary. Omit the ChatGPT alpha search body schema.
