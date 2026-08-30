<!-- capsule-v2 -->
# CORS for credentialed-less public collect endpoints — what response headers make a cross-origin tracker script work?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** Which CORS headers does the collect API return and why is the allowlist exactly those headers?

## collect-cors-fairing
**Path/Symbol:** `src/lib/cors.ts:getApiCorsHeaders/withCorsHeaders/corsPreflight :1-31`; applied at `src/app/api/record/route.ts:117-124, 252` (every exit wrapped).
**Signature:** `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: Content-Type, x-umami-cache`, methods GET/POST/OPTIONS, max-age 86400 (env `CORS_MAX_AGE`).
**Data Shape:** preflight returns 204 with the same header set; error responses get wrapped too (`withCorsHeaders(error())`).

### Decisive source
```ts
export function withCorsHeaders(response: Response, headers: HeadersInit = {}) {
  const nextHeaders = new Headers(response.headers);
  Object.entries(getApiCorsHeaders(headers)).forEach(([key, value]) => {
    nextHeaders.set(key, value);
  });
  return new Response(response.body, { status: response.status, statusText: ..., headers: nextHeaders });
}
```

**Flow:** tracker fetch sends `x-umami-cache` ⇒ browser preflights ⇒ OPTIONS handler returns 204 + headers ⇒ actual POST proceeds; ALL record-route exits (errors included) pass through the wrapper so the browser can read failure bodies.
**Invariant:** the allow-headers list is EXACTLY what the tracker sends (`Content-Type` + `x-umami-cache`) — adding more widens attack surface for no benefit; wildcard origin works because credentials are 'omit' (wildcard + credentials:true is illegal). Wrapping must cover EVERY return path or intermittent opaque failures appear only cross-origin.
**Probe:** structural pins: `grep -n "x-umami-cache" src/lib/cors.ts` → :6; `grep -c "withCorsHeaders" src/app/api/record/route.ts` → ≥10 lines.
**Probe:** `grep -n "corsPreflight" src/app/api/record/route.ts` → :115.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "withCorsHeaders corsPreflight Access-Control", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt exact-header allowlists and wrap-all-exits CORS helpers for any browser-facing ingest API; adapt max-age; omit CSP builder unless you also serve a dashboard app.
