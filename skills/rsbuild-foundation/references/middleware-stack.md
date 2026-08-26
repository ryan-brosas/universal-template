<!-- capsule-v2 -->
# Middleware stack — what is the exact middleware ordering, and how do gzip and proxy interact with it?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce ordering slots (unshift/internals/push), why compression sits after proxy but before everything else, and how the gzip wrapper must handle raw writeHead header arrays.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/devMiddlewares.ts:applySetupMiddlewares` (39–68), `applyDefaultMiddlewares` (70–260), `getDevMiddlewares` (267–300); `server/gzipMiddleware.ts:shouldCompress` (41–66), writeHead/write/end/on wrapping (140–185); `server/proxy.ts:createProxyMiddleware` (38–96).
**Signature:** `getDevMiddlewares({config, buildManager, devServer, context, postCallbacks}): Promise<{close, onUpgrade}>`.
**Data Shape:** connect-next app; setup handlers receive `{unshift, push}` collectors; upgrade events collected into an array fanned out by onUpgrade.

### Decisive source
```ts
// ORDER (applyDefaultMiddlewares): requestLogger(debug) → [user unshift] →
// cors → server.headers → proxy(+ws upgrades) → gzip → lazyCompilationMiddleware →
// baseUrl → /__open-in-editor(lazy launch-editor) → viewingServedFiles(/rsbuild-dev-server) →
// assetsMiddleware(+hot-update.json 404 fallback) → htmlCompletion → publicDir(sirv) →
// [user push callbacks] → historyApiFallback(+assetsMiddleware AGAIN for rewritten urls) →
// htmlFallback → faviconFallback; listen() then appends optionsFallback + notFound LAST.
```
```ts
// gzip: decision at first write — SSE excluded because buffering delays event delivery
if (res.getHeader('Content-Encoding')) return false;             // already compressed
const contentType = res.getHeader('Content-Type'); if (!contentType) return false;
if (!/text|javascript|\/json|xml/i.test(String(contentType))) return false;
if (getMimeType(String(contentType)) === 'text/event-stream') return false;
const size = res.getHeader('Content-Length');
return size === undefined || Number(size) > 1024;
```
```ts
// raw header arrays: dedupe by lowercased key via removeHeader+appendHeader so Set-Cookie multiplies
const setWriteHeadHeaders = (res, headers) => {
  if (Array.isArray(headers)) {
    const seen = new Set<string>();
    for (let i = 0; i < headers.length; i += 2) {
      const key = String(headers[i]); const value = headers[i+1];
      if (value !== undefined) { const k = key.toLowerCase();
        if (!seen.has(k)) { seen.add(k); res.removeHeader(key); }
        res.appendHeader(key, Array.isArray(value) ? value : String(value)); } } }
  else { for (const [k,v] of Object.entries(headers)) if (v !== undefined) res.setHeader(k,v); }
};
```
```ts
// proxy bypass verbs: false → 404; string → rewrite req.url; true → skip to next
if (bypassUrl === false) { res.statusCode = HttpCode.NotFound; next(); }
else if (typeof bypassUrl === 'string') { req.url = bypassUrl; next(); }
else if (bypassUrl === true) { next(); }
else proxyMiddleware(req, res, next);
```

**Flow:** deprecated `dev.setupMiddlewares` warns but still runs, feeding before/after arrays that sandwich ALL internals. Compression placement comment pins both constraints: after proxy (don't break proxied SSE) and before other middleware (compress our own responses). historyApiFallback re-registers assetsMiddleware AFTER itself so rewritten `/index.html` still resolves. Gzip wraps write/end/writeHead/on lazily: decision deferred until first write/start so headers set later still count; Content-Length removed when gzipping; drain→resume plumbing keeps backpressure.

**Invariant:** user push-callbacks run AFTER default internals but BEFORE any fallback middleware (comment: "ideal place... can intercept requests before any fallback handling"); notFound/optionsFallback must remain terminal.

**Probe:** `tests/gzipMiddleware.test.ts:29-59` pins raw-array writeHead with gzip (numeric-index keys never leak as headers); `:62-91` pins multi Set-Cookie preservation through appendHeader path; `:93-121` Content-Length stripped when compressed; `:123-150` pre-encoded identity and missing content-type skip compression; `:177-206` event-stream untouched. `e2e/cases/server/compress-sse/index.test.ts:4-45` pins SSE passthrough inside a real server stack.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "applyDefaultMiddlewares gzipMiddleware createProxyMiddleware setWriteHeadHeaders shouldCompress", limit: 10 });
```

## Verdict
Adopt slot-based user sandwich, compression-after-proxy rule, SSE exclusion, and array-header normalization. Adapt ordering internals to host feature set. Omit launch-editor/viewing-served-files specifics unless porting DX tooling. Coverage caveat: unit tests exist for gzip only; ordering verified from source + e2e.
