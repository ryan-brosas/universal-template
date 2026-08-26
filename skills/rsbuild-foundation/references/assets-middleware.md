<!-- capsule-v2 -->
# Assets middleware — how are dev assets served safely from memory with correct conditional-GET and range behavior?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the URL→file resolution ladder with traversal guards, the ready-queue gating on build completion, and the exact freshness/range decision order.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/assets-middleware/middleware.ts:createAssetsMiddleware` (281–465) — `isPreconditionFailure` (81–106), `isFresh` (112–166), `isRangeFresh` (168–194), stream error mapping (443–456); `getFileFromUrl.ts:getFileFromUrl` (13–107); `setupOutputFileSystem.ts` (5–20); `assets-middleware/index.ts:ready/watch wiring` (275–326).
**Signature:** `createAssetsMiddleware(context, ready, outputFileSystem): RequestHandler`.
**Data Shape:** weak ETag `W/"<size-hex>-<mtime-hex>"`; 512KB read-stream highWaterMark; resolution result `{filename, fsStats} | {errorCode} | undefined`.

### Decisive source
```ts
// security gates BEFORE filesystem work (getFileFromUrl)
if (!pathname) return;                                  // pass through
if (pathname.includes('\0')) return { errorCode: 400 }; // null-byte injection
if (UP_PATH_REGEXP.test(path.normalize(`./${pathname}`))) return { errorCode: 403 };  // traversal

// public-prefix-first resolution, then bare dist joins — Set dedupes duplicates
for (const [index, distPath] of distPaths.entries()) {
  const prefix = publicPathnames[index];
  if (prefix && prefix !== '/' && isUrlPathUnderBase(pathname, prefix))
    possibleFilenames.add(path.join(distPath, pathname.slice(prefix.length)));
}
for (const distPath of distPaths) possibleFilenames.add(path.join(distPath, pathname));
// directory hits retry once with index.html appended
```
```ts
// request ladder inside processRequest
if (isConditionalGET(req.headers)) {
  if (isPreconditionFailure(req.headers, res)) { sendError(res, 412); return; }
  if (isCachable(res.statusCode) && isFresh(req.headers, {etag, 'last-modified'})) {
    res.statusCode = 304;
    for (const h of ['Content-Encoding','Content-Language','Content-Length','Content-Range','Content-Type']) res.removeHeader(h);
    res.end(); return;
  }
}
// ranges: parse combined; stale if-range → full body; -1 → 416 with Content-Range bytes */size;
// -2 malformed or multi-range → log + fall through to FULL response (single range only → 206)
```
```ts
// ready gate: callbacks queued until buildState.status === 'done', flushed via compiler done + process.nextTick
const ready = (cb) => { if (context.buildState.status === 'done') cb(); else callbacks.push(cb); };
```

**Flow:** outputFileSystem is memfs Volume unless writeToDisk resolves true (`setupWriteToDisk` taps emit→assetEmitted writing with mkdir -p, guarded by a `__hasRsbuildAssetEmittedCallback` idempotence symbol); BuildManager re-reads it after init since middleware construction replaces it. Streaming uses createReadStream over the OUTPUT fs with backpressure, HEAD short-circuits after headers, stream errors map ENAMETOOLONG/ENOENT/ENOTDIR→404 else 500, cleanup destroys streams on finish/error suppressing late error listeners.

**Invariant:** never stat or read outside resolved dist paths (all candidate paths are joins under known roots); 304 must strip entity headers; If-Range with weak ETag must degrade to full response (strong comparison only).

**Probe:** `e2e/cases/server/serve-assets/index.test.ts` exercises served assets end-to-end; direct unit coverage absent upstream for isFresh ladder (coverage caveat: deterministic source read; gzip interplay covered separately by gzipMiddleware tests). Malicious-path logging pinned at middleware.ts:317-321.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createAssetsMiddleware getFileFromUrl isFresh isRangeFresh setupOutputFileSystem", limit: 10 });
```

## Verdict
Adopt the guard-order (decode → null-byte → traversal), prefix-first resolution, ready-queue, and header-stripping 304 ladder. Adapt mime table (mrmime) and ETag formula as needed. Omit HTTP/2-specifics. Coverage caveat: no unit runner this run.
