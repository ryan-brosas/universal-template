<!-- capsule-v2 -->
# Dev-server HTML fallback ladder — why do completion and fallback middlewares re-invoke the assets middleware instead of serving files?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the request-classification gate, the two distinct HTML rewrites, and the base-URL redirect/not-found split.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/middlewares.ts` — `maybeHTMLRequest` 103–117, `getUrlPathname` 119–123 (strip `[?#]`), `getHtmlCompletionMiddleware` 134–175, `getHtmlFallbackMiddleware` 229–254, `getBaseUrlMiddleware` 180–224; siblings `historyApiFallback.ts` 15–121 (dot-rule 101–104), favicon 10–17, options 69–78, viewingServedFiles `/rsbuild-dev-server`.
**Signature:** `getHtmlCompletionMiddleware({distPaths, assetsMiddleware, outputFileSystem})`, `getBaseUrlMiddleware({base})`.
**Data Shape:** distPaths array checked via outputFileSystem.stat (memfs-compatible); rewrite = mutate `req.url` then call `assetsMiddleware(req,res,next)` directly.

### Decisive source
```ts
const maybeHTMLRequest = (req) => req.url && req.headers && (req.method==='GET'||req.method==='HEAD')
  && typeof req.headers.accept === 'string' && (accept.includes('text/html') || accept.includes('*/*'));
// '/'  => '/index.html'      (trailing slash)
// '/main' => '/main.html'    (no extension)
if (await isFileExistsInDistPaths(distPaths, newUrl, outputFileSystem)) { req.url = newUrl; assetsMiddleware(req,res,next); return; }
```
```ts
if (isUrlPathUnderBase(pathname, base)) { req.url = removeBasePath(url, base); next(); return; }
const redirectPath = addTrailingSlash(url) !== base ? joinUrlPath(base, url) : base;
if (pathname === '/' || pathname === '/index.html') { res.writeHead(302, {Location: redirectPath}); ... }   // root → based URL w/ search+hash
else if (accept text/html) → styled 404 hint page; else plain-text 404 for resources.
```

**Flow:** htmlFallback runs LAST: any unmatched HTML-ish GET whose `index.html` exists in ANY dist path is rewritten to it (SPA history support) — but never for `/favicon.ico`. Completion middleware only fires when target file EXISTS (checked per distPath), so missing pages still 404 naturally. History-fallback variant honors explicit rewrites + dot-rule (`pathname.lastIndexOf('.') > lastIndexOf('/')` blocks rewriting asset-ish paths).
**Invariant:** (1) classification requires BOTH method and Accept header — API clients with `*/*`... wait: `*/*` IS accepted, JSON-preferring clients are excluded upstream in historyApiFallback via `accept.startsWith('application/json')`; (2) existence checks MUST go through outputFileSystem (dev assets live in memfs, not disk); (3) rewrites call the assets middleware DIRECTLY so ETag/range logic applies to the rewritten URL.
**Probe:** e2e `cases/server/html-fallback/index.test.ts:4/:27/:43/:70` (default on / false 404s / query+hash / main.html); `server/base-url/index.test.ts:3/:45/:66/:103` (dev/preview/query/base-subpath).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "getHtmlCompletionMiddleware getHtmlFallbackMiddleware getBaseUrlMiddleware maybeHTMLRequest historyApiFallbackMiddleware", limit: 8 });
```

## Verdict
Adopt the three-tier ladder (completion → base-URL → SPA fallback), memfs-aware existence probes, direct-middleware rewrite chaining, and root-302-with-query. Adapt route names and the `/rsbuild-dev-server` inspector to host. Omit the embedded CSS of the assets report page.
