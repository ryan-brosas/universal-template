<!-- capsule-v2 -->
# GUI shell serving & SPA fallback — how does one middleware decide between static assets, branded index shells, and doing nothing?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When does GuiMiddleware terminate a request vs fall through, and what three conditions disable it entirely?

## Constructor-time tri-state + Accept-header branch
**Path/Symbol:** `packages/nocodb/src/middlewares/gui/gui.middleware.ts:GuiMiddleware` (whole 82L).
**Signature:** constructor builds `{staticRouter, indexHtml} | null`; `async use(req, res, next)`; `getIndexHtml(): string | null`.
**Data Shape:** disabled by ANY of — NC_DASHBOARD_URL starting with http (split frontend), missing NC_GUI_DIST_PATH, missing dist/index.html; enabled otherwise with express.static(distPath).

### Decisive source
```ts
const wantsHtml = req.headers.accept?.includes('text/html');
if (!wantsHtml) {
  return this.staticRouter(req, res, next);   // real static files, fall through when unmatched
}
let html = this.indexHtml;
try { html = await injectBrandingMeta(html, req); }
catch { html = this.indexHtml; }              // injection failure → unmodified shell
res.setHeader('Content-Type', 'text/html');
res.send(html);
```
(:55–:71)

**Flow:** constructor resolves tri-state ONCE (dist availability fixed for process life) → inert instances return `next()` immediately → frame-guard headers set BEFORE branching because this middleware TERMINATES the shell path (GlobalMiddleware never runs for anything served here — including `<object>` embed fetches of `/` with `Accept: */*`) → non-HTML Accept goes to express.static with fall-through → HTML navigation gets the shell with white-label brand injected best-effort.
**Invariant:** the frame-guard-before-branch ordering is load-bearing (comment :43–:47): terminating middlewares own the security headers of everything they serve. Brand injection must be failure-tolerant (crawler-visible branding is cosmetic; a throw must never 500 the app shell). getIndexHtml exists so entry points can reuse the same shell resolution.
**Probe:** `cd packages/nocodb && grep -c "return next()" src/middlewares/gui/gui.middleware.ts` (=1 inert-instance site :44; static-miss fall-through rides express.static's own next) and `grep -c "NC_GUI_DIST_PATH\|NC_DASHBOARD_URL" src/middlewares/gui/gui.middleware.ts` (=4: comment+read for each env).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "GuiMiddleware injectBrandingMeta staticRouter wantsHtml NC_GUI_DIST_PATH", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tri-state disable + Accept branching + header ownership by terminating middleware; adapt branding injection to your theming; omit entirely behind a reverse proxy serving statics. Coverage caveat: gui.middleware.spec.ts is an empty describe stub — probes are greps.
