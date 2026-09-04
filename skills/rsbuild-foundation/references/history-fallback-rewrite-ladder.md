<!-- capsule-v2 -->
# historyApiFallback rewrite ladder — why does the dot-rule use lastIndexOf comparison and JSON-preferring clients get skipped?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the SPA fallback gate order and its escape hatches.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/historyApiFallback.ts` — method/accept gates 27–63 (application/json prefix check 44–48), rewrites loop 75–98, dot rule 101–114 (`pathname.lastIndexOf('.') > pathname.lastIndexOf('/')` + disableDotRule), index 116–119; `parseReqUrl` 123–131 (x-forwarded-proto/host aware).
**Signature:** `historyApiFallbackMiddleware(logger, options?): RequestHandler`.
**Data Shape:** HistoryApiFallbackOptions {rewrites?: {from: RegExp, to: string | fn}[], htmlAcceptHeaders?, disableDotRule?, index?}.
**Provenance:** modified from bripkens/connect-history-api-fallback (MIT) — attribution header lines 1–8.

### Decisive source
```ts
if (headers.accept.startsWith('application/json')) { next(); return; }   // API clients never rewritten
...
if (pathname && pathname.lastIndexOf('.') > pathname.lastIndexOf('/') && options.disableDotRule !== true) {
  next(); return;   // '/static/js/chunk.abc.js' has a dot AFTER the last slash → asset-ish → skip
}
req.url = index; next();   // everything else → SPA index
```
```ts
function parseReqUrl(req) {
  const proto = req.headers['x-forwarded-proto'] || 'http';
  const host = req.headers['x-forwarded-host'] || req.headers.host || LOCALHOST;
  try { return new URL(req.url || '/', `${proto}://${host}`); } catch { return null; }
}
```

**Flow:** explicit rewrites run FIRST (first match wins; non-absolute targets log a recommendation); the dot-rule then protects real asset paths from being swallowed; only clean routes fall through to index. URL parsing behind proxies uses forwarded headers so rewrites see the client-facing path.
**Invariant:** (1) the dot-rule compares POSITIONS not existence — `/v1.2/users` is rewritable (dot before last slash) while `/app.min.js` is not; (2) accept.startsWith('application/json') intentionally misses `application/json; charset=utf-8`... upstream accepts that trade-off; a porter hardening this must keep the debug-log parity; (3) parse failure returns null → skip (never throw inside middleware).
**Probe:** e2e `cases/server/html-fallback/index.test.ts:4/:27/:43/:70` covers the sibling middleware family; direct suite absent for this file at pin (coverage caveat: deterministic read + lineage).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "historyApiFallbackMiddleware parseReqUrl disableDotRule", limit: 8 });
```

## Verdict
Adopt gate order (method→accept→rewrites→dot-rule→index) verbatim. Adapt option names to host. Omit verbose debug logging if host logger differs.
