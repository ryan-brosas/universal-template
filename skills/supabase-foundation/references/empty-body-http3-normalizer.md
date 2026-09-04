<!-- capsule-v2 -->
# Empty-body HTTP/3 normalizer — why do 201-with-empty-body responses succeed on HTTP/2 but throw "Unexpected end of JSON input" on HTTP/3?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How do I make a JSON-parsing HTTP client treat transport-dependent empty success bodies as empty instead of a parse crash?

## normalizeEmptyBodyResponse
**Path/Symbol:** `apps/studio/data/fetchers.ts:76-93` (`normalizeEmptyBodyResponse`), installed in the `onResponse` middleware (:128-131).
**Signature:** `export async function normalizeEmptyBodyResponse(response: Response): Promise<Response>`.
**Data Shape:** Input is an ok (`response.ok`) Response; output is either the identical Response object (non-empty body, 204, or Content-Length already present) or a rebuilt Response with the same status/statusText/headers plus `Content-Length: 0` and a null body.

### Decisive source
```ts
/**
 * openapi-fetch only treats a response body as empty when `status === 204` or the
 * response carries a `Content-Length: 0` header; otherwise it calls `response.json()`,
 * which throws "Unexpected end of JSON input" on an empty body. HTTP/3 (and HEAD
 * requests) may omit `Content-Length: 0` on empty-body responses — e.g. a `201` with
 * no body — so a request that succeeds over HTTP/2 can fail over HTTP/3.
 *
 * Normalize empty-body success responses by setting `Content-Length: 0` so the parser
 * short-circuits regardless of transport. Non-empty responses are returned untouched.
 */
export async function normalizeEmptyBodyResponse(response: Response): Promise<Response> {
  if (response.status === 204 || response.headers.has('Content-Length')) {
    return response
  }
  const body = await response.clone().text()
  if (body.length > 0) {
    return response
  }
  const headers = new Headers(response.headers)
  headers.set('Content-Length', '0')
  return new Response(null, {
    status: response.status,
    statusText: response.statusText,
    headers,
  })
}
```

**Flow:** ok response → already 204 or has any Content-Length header → passthrough (zero cost) → otherwise clone and read text once → non-empty returns the original untouched → empty rebuilds with `Content-Length: 0`, so the client's parser short-circuits before calling `.json()`.
**Invariant:** the clone-and-read must happen on `response.clone()` so the original body stream stays consumable downstream; a rebuilt response never changes status, statusText, or existing headers — it only adds the one length marker. Non-empty bodies must be returned as the ORIGINAL object (not a copy) to preserve streaming semantics.
**Probe:** `apps/studio/data/normalizeEmptyBodyResponse.test.ts` (direct upstream suite, read in full this pass): pins the HTTP/3 empty-201 normalization (:12-24), passthrough when Content-Length already present (:26-35), original-object return with body still readable for non-empty responses (:37-49), 204 untouched (:51-57), status/statusText preservation (:59-66), other-header preservation (:68-78), plus an end-to-end client case stubbing global fetch so a bare empty-201 RESOLVES with `data = {}` instead of throwing (:81-101). Run `vitest run normalizeEmptyBodyResponse.test.ts` from apps/studio where node_modules exist (blocked in-lane at this pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "normalizeEmptyBodyResponse", limit: 5 });
```

## Verdict
Adopt the mechanism verbatim for any client whose JSON parser dispatches on status/headers rather than actual body emptiness — it is a three-branch pure function. Adapt the trigger condition if your client's emptiness rule differs (this exact rule is openapi-fetch's). Omit nothing: skipping the clone or copying non-empty responses are the two realistic wrong ports.
