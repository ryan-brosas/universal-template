<!-- capsule-v2 -->
# Dual fetch plane — when must I use the legacy fetchGet/fetchPost trio instead of the typed client, and what compat hack keeps old callers alive?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** If my app has both a typed OpenAPI client and ad-hoc dashboard endpoints, what contract must the legacy escape-hatch helpers follow so error handling stays uniform across both planes?

## Legacy fetch trio + self-referencing error shim
**Path/Symbol:** `apps/studio/data/fetchers.ts`: doc-comment split (:247-248, :316-318), `handleFetchResponse` (:250-265), `handleFetchHeadResponse` (:267-280), `handleFetchError` (:282-314), `fetchGet` (:319-342), `fetchPost` (:349-374), `fetchHeadWithTimeout` (:379-407).
**Signature:** `fetchGet<T>(url: string, options?): Promise<T | ResponseError>`; `fetchPost<T>(url, data, options?)`; `fetchHeadWithTimeout<T>(url, headersToRetrieve: string[], options?)`.
**Data Shape:** Return is a union — parsed payload (JSON object, plain text, or raw Response for octet-stream) OR a ResponseError; callers branch on the union rather than try/catch.

### Decisive source
```ts
async function handleFetchResponse<T>(response: Response): Promise<T | ResponseError> {
  const contentType = response.headers.get('Content-Type')
  if (contentType === 'application/octet-stream') return response as any
  const resTxt = await response.text()
  try {
    return JSON.parse(resTxt)
  } catch (err) {
    return resTxt as any // plain-text passthrough
  }
}

async function handleFetchError(response: unknown): Promise<ResponseError> {
  let resJson: any = {}
  if (response instanceof Error) resJson = response
  if (response instanceof Response) resJson = await response.json()
  const status = response instanceof Response ? response.status : undefined
  const message = resJson.message ?? resJson.msg ?? resJson.error ??
    `An error has occurred: ${status ?? 'Unknown error'}`
  // ...Retry-After ?? X-RateLimit-Reset -> retryAfter...
  let error = new ResponseError(message, status, undefined, retryAfter)
  // @ts-expect-error - many of our local api routes check `if (response.error)`.
  // This is a fix to keep those checks working without breaking changes.
  error.error = error
  return error
}
```

**Flow:** legacy helper → constructHeaders (same identity/auth rules as the typed plane) → native fetch with `referrerPolicy: 'no-referrer-when-downgrade'` and caller abort signal → not ok: handleFetchError (message ladder message→msg→error→status fallback, retryAfter parse, self-reference install) → ok: octet-stream returns the raw Response; otherwise text→JSON→plain-text degradation.
**Invariant:** these helpers are for DASHBOARD endpoints only (both doc comments say so — use the typed client or bare fetch for platform APIs); errors RESOLVE rather than throw (`Promise<T | ResponseError>`), inverting the typed plane's throw-on-error model; HEAD projects only the requested header names into an object under `AbortSignal.timeout(options?.timeout ?? 60000)`; the `error.error = error` self-reference is an explicit compatibility shim for `if (response.error)` checks — new code should test `instanceof ResponseError` instead.
**Probe:** no dedicated upstream unit test for the trio (verified by graph search over apps/studio/data/*; database-queue tests mock executeSql, unrelated) — caveat recorded; probe by construction: stub fetch returning `{ok:false, status:503, json: async () => ({message:'feature flag is required'})}` and assert the resolved value is a ResponseError whose `.error` property is itself (`error.error === error`) and whose message equals `'feature flag is required'`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "fetchGet fetchPost handleFetchError legacy", file_pattern: "apps/studio/data/*", limit: 10 });
```

## Verdict
Adopt the two-plane split as a deliberate architecture: typed client throws classified errors, legacy helper resolves unions — never mix the models on one endpoint. Adopt the message ladder (message→msg→error→status-template) and octet-stream/HEAD special cases. Adapt the compat shim: keep it only while legacy call sites exist, and prefer the source's stated future direction (`instanceof ResponseError`). Omit the dashboard-specific endpoint set.
