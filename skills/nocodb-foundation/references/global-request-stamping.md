<!-- capsule-v2 -->
# Global request stamping — which five request fields must exist before ExtractIds runs, and why does tab-id validation matter?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does the outermost middleware guarantee about `req` shape for everything downstream?

## Site-url/tab-id/dashboard stamps + frame-guard delegation
**Path/Symbol:** `packages/nocodb/src/middlewares/global/global.middleware.ts:GlobalMiddleware.use` (:17–:38 whole file 40L).
**Signature:** `use(req, res, next)` — synchronous; sets `req.ncSiteUrl`, `req.ncFullUrl`, `req.ncTabId`, `req.dashboardUrl`; delegates `setFrameGuardHeaders(req, res)`.
**Data Shape:** ncSiteUrl = configured `Noco.config.ncSiteUrl || protocol://host`; tab id accepted ONLY matching UUID-v4 regex `/^[0-9a-f]{8}-...-[0-9a-f]{12}$/i`.

### Decisive source
```ts
setFrameGuardHeaders(req, res);   // covers API responses + dev SPA shell (comment: GuiMiddleware inert cases)
req.ncSiteUrl = Noco.config?.ncSiteUrl || req.protocol + '://' + req.get('host');
// ...
const rawTabId = req.headers?.['x-nc-tab-id'];
if (ncIsString(rawTabId) && TAB_ID_RE.test(rawTabId)) {
  req.ncTabId = rawTabId;
}
```
(:20–:31)

**Flow:** runs before route middlewares → frame headers emitted here for API+dev paths → site-url resolution prefers explicit config over Host header (host-header-injection surface narrowed to config-less deployments) → tab id from client header validated against strict regex BEFORE storage because it later keys per-tab undo stacks and context propagation (`context.tab_id`) — an unvalidated header would let clients collide or poison other tabs' stack filters → dashboard URL env override documented as playwright-only.
**Invariant:** validation-before-storage is the whole capsule — downstream consumers index by tab_id trusting the format; the frame-guard call must precede any response-producing branch in THIS middleware since it's the only pass through for API routes.
**Probe:** `cd packages/nc-gui 2>/dev/null; cd packages/nocodb && grep -n "TAB_ID_RE" src/middlewares/global/global.middleware.ts` (:9 definition + :27 test, one pair — ERRATUM pass 19 audit: shipped cites said :13/:29) and `grep -c "req\.[a-zA-Z]* =" src/middlewares/global/global.middleware.ts` (=4 stamped fields: ncSiteUrl, ncFullUrl, ncTabId, dashboardUrl — shipped count of 6 over `req\.` included the header read and host getter; re-derived against live source :22-:37).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "GlobalMiddleware ncSiteUrl ncTabId x-nc-tab-id TAB_ID_RE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stamp-once-early with format-validated client input; adapt header names/config keys; omit dashboard URL if no SPA. Coverage caveat: global.middleware.spec.ts empty stub at pin.
