<!-- capsule-v2 -->
# pg-meta fail-fast guard + error-enrichment middleware — where do errors get requestId/retryAfter/code/requestPathname injected, and when does the client refuse to hop to the database at all?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What must the client's onRequest/onResponse middleware pair do so every downstream consumer receives errors carrying correlation and backoff fields, without wasting a server round-trip on requests that are guaranteed to fail?

## pgMetaGuard + onResponse enrichment
**Path/Symbol:** `apps/studio/data/fetchers.ts`: `pgMetaGuard` (:95-114), `client.use({onRequest}, {onResponse})` (:116-162).
**Signature:** `function pgMetaGuard(request: Request): Request`; middleware hooks `async onRequest({ request })` / `async onResponse({ request, response })`.
**Data Shape:** Error response bodies are rewritten in-flight to `{...body, code: number, requestId: string|null, retryAfter?: number, requestPathname: string}` — the exact field contract the classification ladder (`handle-error-classification-ladder.md`) and the retry gate (`react-query-data-module-recipe.md`) consume.

### Decisive source
```ts
function pgMetaGuard(request: Request) {
  // Only check for /platform/pg-meta/ endpoints
  if (request.url.includes('/platform/pg-meta/')) {
    // If there is no valid `x-connection-encrypted`, pg-meta will necesseraly fail
    // to connect to the target database in such case, we save the hops and throw
    if (!isValidConnString(request.headers.get('x-connection-encrypted'))) {
      const retryAfterHeader = request.headers.get('Retry-After')
      throw new ResponseError(
        'API Error: happened while trying to acquire connection to the database',
        400,
        request.headers.get('X-Request-Id') ?? undefined,
        retryAfterHeader ? parseInt(retryAfterHeader) : undefined
      )
    }
    if (!request.headers.get('x-pg-application-name')) {
      request.headers.set('x-pg-application-name', DEFAULT_PLATFORM_APPLICATION_NAME)
    }
  }
  return request
}

async onResponse({ request, response }) {
  if (response.ok) return normalizeEmptyBodyResponse(response)
  try {
    let body = await response.clone().json()
    body.code = response.status
    body.requestId = request.headers.get('X-Request-Id')
    const retryAfterHeader =
      response.headers.get('Retry-After') ?? response.headers.get('X-RateLimit-Reset')
    body.retryAfter = retryAfterHeader ? parseInt(retryAfterHeader) : undefined
    const requestUrl = new URL(request.url)
    body.requestPathname = requestUrl.pathname
    return new Response(JSON.stringify(body), {
      headers: response.headers,
      status: response.status,
      statusText: response.statusText,
    })
  } catch {
    // noop
  }
  return response
}
```

**Flow:** onRequest → constructHeaders → pgMetaGuard (connection-string preflight + application-name defaulting, pg-meta routes only) → server → onResponse → ok: empty-body normalization; error: clone-parse JSON, inject code/requestId/retryAfter/requestPathname, re-wrap with ORIGINAL status/headers. JSON parse failure silently returns the untouched Response.
**Invariant:** the guard throws BEFORE any network I/O for pg-meta routes lacking a connection string — the failure is local and cheap by design ("save the hops"); enrichment must preserve the original status/statusText/headers on the rebuilt Response so HTTP semantics survive; Retry-After wins over X-RateLimit-Reset (left-to-right ??); a non-JSON error body is passed through unmodified rather than fabricated.
**Probe:** no dedicated upstream test for the middleware (only handleError.test.ts exists for this module) — caveat recorded; probe by construction: run a typed call against a stub fetch returning `{status: 500, body: {message: 'x'}}` plus a `Retry-After: 7` header and assert the surfaced error object carries `code: 500`, string requestId matching the minted uuid, and `retryAfter === 7`.
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "supabase", function_name: "supabase.apps.studio.data.fetchers.pgMetaGuard", direction: "both", depth: 1 });
```

## Verdict
Adopt the four-field enrichment grammar (code/requestId/retryAfter/requestPathname) as the wire contract between your client layer and your cache/retry layer — it is what makes server-driven backoff possible. Adapt which routes get the fail-fast guard (Supabase scopes it to `/platform/pg-meta/` + encrypted-connection-string semantics); omit nothing else. Coverage: `no_recorded_issue + metadata_match` @ gen 2026-08-25T19:56:24Z.
