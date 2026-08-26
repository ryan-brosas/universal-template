<!-- capsule-v2 -->
# Static web-dir gate — how do you serve a vendored SPA under mounted prefixes without feeding HTML to asset requests?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** a built SPA must be reachable at `/member/*` and `/ui/*` while its assets live at `/static/*` — how does one GET handler serve both without triggering the classic "Unexpected token '<'" white screen?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts` — static plane inline in `handle` (511-534) + `serveFile` (538-547). Graph: search_graph "static webDir index.html extension SPA fallback serveFile" (file_pattern server.ts) -> total 1: `serveFile` 538-547; the prefix/fallback ladder is part of the enclosing `handle` dispatcher (see loopback-control-plane for the gate that precedes it).
**Signature:** inline in `handle(req,res,ctx)` after all API routes; `serveFile(res, path: string): void`.
**Data Shape:** request path -> optional prefix strip (`/member/`, `/ui/`) -> webDir-relative file; SPA fallback condition = `Accept` includes `text/html` AND pathname has no file extension.

### Decisive source
```ts
let pathname = url.pathname;
if (pathname.startsWith("/member/")) pathname = pathname.slice("/member".length) || "/";
if (pathname.startsWith("/ui/"))     pathname = pathname.slice("/ui".length) || "/";
if (pathname === "/") pathname = "/index.html";
let filePath = join(webDir, pathname);
if (!filePath.startsWith(webDir)) { json(res, 403, { error: "forbidden" }); return; }
let stat = null;
try { stat = statSync(filePath); } catch { /* missing */ }
if (stat && stat.isFile()) { serveFile(res, filePath); return; }
// SPA fallback: only for HTML-navigation requests, never for asset paths
const wantsHtml = (req.headers.accept ?? "*").includes("text/html");
const hasExt = /\.[a-z0-9]+$/i.test(pathname);
if (wantsHtml && !hasExt) {
  const fallback = join(webDir, "index.html");
  if (existsSync(fallback)) { serveFile(res, fallback); return; }
}
```
**Flow:** only GET reaches this plane; everything else already 404'd through the API ladder. Existing files win over the fallback, so deep-linked real assets never get index.html. `serveFile` maps html/js/mjs/css/json/svg/ico content types (charset-pinned for text) and defaults to application/octet-stream via readFileSync.
**Invariant:** an extension-bearing path can NEVER receive index.html even when missing — that is precisely the white-screen regression guard (a missing chunk returning HTML parses as `Unexpected token '<'`). The traversal guard is defense-in-depth, not primary: WHATWG `new URL()` has already collapsed `..` dot segments before the string-prefix check runs. Prefix strips preserve the rest of the path so hashed chunk names survive remapping.
**Probe:** no upstream unit test covers the static plane directly (coverage caveat); li-proxy.test.ts boots the full server so static behavior is exercised indirectly. Deterministic evidence executed this pass: direct checkout read of server.ts 498-547 matched graph snippet bytes for serveFile; coverage check `no_recorded_issue` @ gen 2026-08-23T00:33:18Z; `pnpm test` exit 0 (9/9) against the same handler chain.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ultireaaach",
  qualified_name: "ultireaaach.packages.app.src.server.serveFile" });
// observed this pass: server.ts 538-547 — ext->MIME map + readFileSync end()
```

## Verdict
Adopt the two-condition SPA fallback (HTML navigation AND extension-less) plus existing-file-wins ordering for any single-handler static server with mounted prefixes. Adapt prefix vocabulary to your routes. Watch the MIME default: octet-stream for unknown extensions is what keeps font/image hashes intact.
