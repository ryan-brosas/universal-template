<!-- capsule-v2 -->
# OpenAPI client kernel — how do I assemble one typed fetch client whose transport translates network failures and mints per-request identity headers?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What must a shared typed API client guarantee about its transport shim and header construction so every data module gets identical network-error text and traceable request IDs?

## Typed client assembly + transport shim + identity headers
**Path/Symbol:** `apps/studio/data/fetchers.ts`: `fetchHandler` (:18-28), `client = createClient<paths>` (:30-43), `constructHeaders` (:52-64).
**Signature:** `export const fetchHandler: typeof fetch = async (input, init) => {...}`; `export function constructHeaders(headersInit?: HeadersInit | undefined): Promise<Headers>`.
**Data Shape:** `fetchHandler` is installed as openapi-fetch's `fetch`. `constructHeaders` takes an optional caller HeadersInit and returns an enriched `Headers`; it is consumed both by the client's `onRequest` middleware and by the legacy fetch trio.

### Decisive source
```ts
export const fetchHandler: typeof fetch = async (input, init) => {
  try {
    return await fetch(input, init)
  } catch (err: any) {
    if (err instanceof TypeError && err.message === 'Failed to fetch') {
      console.error(err)
      throw new Error('Unable to reach the server. Please check your network or try again later.')
    }
    throw err
  }
}

export const client = createClient<paths>({
  fetch: fetchHandler,
  baseUrl: API_URL?.replace('/platform', ''),
  referrerPolicy: 'no-referrer-when-downgrade',
  headers: DEFAULT_HEADERS,
  credentials: 'include',
  querySerializer: { array: { style: 'form', explode: false } },
})

export async function constructHeaders(headersInit?: HeadersInit | undefined) {
  const requestId = uuidv4()
  const headers = new Headers(headersInit)
  headers.set('X-Request-Id', requestId)
  if (!headers.has('Authorization')) {
    const accessToken = await getAccessToken()
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return headers
}
```

**Flow:** every typed call → openapi-fetch → `onRequest` middleware calls `constructHeaders()` → fresh uuid `X-Request-Id`, Bearer token added only when absent → `pgMetaGuard(request)` → `fetchHandler` wraps native fetch; a browser-level `TypeError: Failed to fetch` becomes a human-actionable Error; all other throws pass through untouched.
**Invariant:** exactly one new `X-Request-Id` per request; an explicit caller-supplied Authorization header is never overwritten (the `headers.has` guard precedes `getAccessToken()`); the transport translation matches ONLY that one exact TypeError message — any other rejection is rethrown as-is so downstream error handling sees the original failure.
**Probe:** `apps/studio/data/handleError.test.ts` mocks `common`/`@/lib/helpers` (`uuidv4: () => 'test-uuid'`) before importing `./fetchers`, proving the module is importable in isolation and the uuid helper is injectable; run `vitest run handleError.test.ts` from `apps/studio` where node_modules exist (blocked in-lane at this pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "fetchHandler constructHeaders fetch wrapper", file_pattern: "apps/studio/data/*", limit: 10 });
```

## Verdict
Adopt the transport-translation contract (single-message TypeError mapping), per-request uuid identity header, and auth-only-if-absent rule verbatim; adapt the token source (`getAccessToken`) and base-URL normalization to your host; omit the `/platform` suffix strip (Supabase env topology) and the temporary-comment caveat once your env vars carry base URLs. Coverage: `no_recorded_issue + metadata_match` @ gen 2026-08-25T19:56:24Z.
