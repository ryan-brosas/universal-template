<!-- capsule-v2 -->
# Proxy Fetch + Origin-Scoped Redirects — how do custom secret headers survive redirects and proxies safely?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** Native fetch strips `Authorization`/`Cookie` on cross-origin redirects but PRESERVES arbitrary custom header names — so how does a client carrying secrets in headers like `X-API-Key` follow redirects without leaking them to a different origin?

## Manual redirect loop with per-hop header re-scoping
**Path/Symbol:** `packages/shadcn/src/registry/proxy.ts:84-132` (`fetchWithProxy`, `MAX_REDIRECTS`, `SAFE_HEADER_NAMES`), `:134-173` (`fetchOnce`), `:4-78` (proxy dispatcher ladder).
**Signature:** `fetchWithProxy(url: string | URL, init?: RequestInit) => Promise<Response>`; `createProxyDispatcher(env?) => Dispatcher | undefined`.
**Data Shape:** `MAX_REDIRECTS = 5`; `SAFE_HEADER_NAMES = new Set(["accept","user-agent"])`. Dispatcher selection: SOCKS via `ALL_PROXY`/`all_proxy` (schemes socks:→5, socks4:/socks4a:→4, socks5:/socks5h:→5, default port 1080, URL-credential decoding) else undici `EnvHttpProxyAgent` when any of HTTPS_PROXY/https_proxy/HTTP_PROXY/http_proxy is set, else undefined.

### Decisive source
```ts
// Standard fetch strips Authorization/Cookie/Proxy-Authorization on
// cross-origin redirects, but preserves custom-named headers. Since private
// registries can carry secrets in arbitrary header names (e.g. X-API-Key), we
// follow redirects manually and only re-attach the caller's headers when the
// next hop stays on the original origin.
for (let i = 0; i <= MAX_REDIRECTS; i++) {
  const response = await fetchOnce(currentUrl, init, headers)
  if (!(response.status >= 300 && response.status < 400 && response.headers.has("location"))) {
    return response
  }
  const nextUrl = new URL(response.headers.get("location")!, currentUrl)
  if (nextUrl.origin !== originalOrigin) {
    // Cross-origin hop: drop every caller-supplied header except Accept/User-Agent.
    const stripped = new Headers()
    originalHeaders.forEach((value, key) => {
      if (SAFE_HEADER_NAMES.has(key.toLowerCase())) stripped.set(key, value)
    })
    headers = stripped
  } else {
    headers = originalHeaders          // same-origin: restore full headers
  }
  currentUrl = nextUrl.toString()
}
throw new Error(`Too many redirects while fetching ${url}`)
```

**Flow:** fetch with `redirect:"manual"` + optional dispatcher → 3xx+Location → relative-resolve next URL → origin comparison decides full-header restore vs strip-to-{accept,user-agent} → repeat ≤5 → hard error past budget. Network failures unwrap `TypeError.cause` into `Request to <url> failed, reason: <cause>`; AggregateError `.errors[0]` recursed for per-address reasons (ECONNREFUSED etc.).
**Invariant:** Caller-supplied secret headers must NEVER cross the original origin; same-origin hops must restore ALL caller headers (not accumulate stripping). Redirect handling must stay manual (`redirect:"manual"`) because native auto-redirect would silently forward custom header names. The global `fetch` binding must be kept (not undici's import) so test interceptors like MSW keep working.
**Probe:** `packages/shadcn/src/registry/proxy.integration.test.ts` (spins real proxy servers from env-var matrix) exists but requires network-loopback fixtures; runner absent in this read-only checkout (no node_modules) — behavior pinned by direct source read of the module and its inline contract comments. Recorded caveat: no executed probe this pass.
**Coverage:** proxy.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "fetchWithProxy redirect cross-origin headers proxy dispatcher", limit: 10 });
```

## Verdict
Adopt the origin-scoped redirect policy verbatim whenever requests carry credentials in non-standard headers — the threat model comment is the porting spec. Adapt SAFE_HEADER_NAMES to your non-sensitive set. Adopt the dispatcher ladder only for Node/undici hosts; browsers handle proxies out of band. Omit the MSW-compatibility rationale in production code (test-only concern).
