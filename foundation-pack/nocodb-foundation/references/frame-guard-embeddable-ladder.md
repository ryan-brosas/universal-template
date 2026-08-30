<!-- capsule-v2 -->
# Frame-guard embeddability ladder — which paths must stay framable, and where do BOTH security headers get set vs deliberately omitted?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the server frame-lock everything except published share embeds without breaking legacy hash-fragment embeds?

## Four-class path ladder + dual-header lock
**Path/Symbol:** `packages/nocodb/src/helpers/frameGuard.ts:setFrameGuardHeaders` (:65–:76 whole file 76L).
**Signature:** `(req: {path?: string}, res: {setHeader(name, value): void}) => void` — pure function, no deps, called from GlobalMiddleware AND GuiMiddleware.
**Data Shape:** emits ZERO headers for exempt paths (X-Frame-Options has no path notion — per-path CSP only works because frame-ancestors IS path-scopable but they chose omit-not-relax), else `X-Frame-Options: SAMEORIGIN` + `Content-Security-Policy: frame-ancestors 'self'`.

### Decisive source
```ts
const EMBEDDABLE_SHARE_ROUTE =
  /^\\/(?:nc\\/(?:view|form|grid|gallery|kanban|calendar|map|list|timeline|gantt|dashboard|interface|base|p)|base|doc)\\/[^/]+/;
function isEmbeddablePath(path: string): boolean {
  return (
    EMBEDDABLE_SHARE_ROUTE.test(path) ||
    isCustomUrlRedirect(path) ||   // /p/<customPath> 302 hop
    isLegacyHashShell(path) ||     // /dashboard or / — legacy #/nc/view/* embeds
    isPublicShareApi(path)         // /api/v2/public/, /api/v1/db/public/
  );
}
if (isEmbeddablePath(path)) { return; }
res.setHeader('X-Frame-Options', 'SAMEORIGIN');
res.setHeader('Content-Security-Policy', "frame-ancestors 'self'");
```
(:13–:14, :52–:75)

**Flow:** every response passes through exactly one of the two callers (GlobalMiddleware covers API+dev SPA; GuiMiddleware covers the built shell and terminates before GlobalMiddleware — it sets the header itself, comment :15–:18) → embeddable paths get NOTHING → everything else gets BOTH headers. Legacy hash-shell exemption exists because fragment routes never reach the server as fragments; boundary enforcement moves one layer up to nc-gui's client middleware 403.
**Invariant:** MUST stay in sync with the five share-link builder components (in-file list) or the missed route's embeds break with "refused to connect"; the `/p/` redirect hop must stay header-free because browsers evaluate frame-ancestors on REDIRECT responses too. Setting only ONE of the two headers defeats older browsers (XFO ignored when CSP present? no — both eras need coverage); setting them on the shell breaks every pre-clean-URL embed with no server-side recourse.
**Probe:** `cd packages/nocodb && grep -c "setHeader" src/helpers/frameGuard.ts` (=2 emit sites + 1 type signature =3 matches) and `grep -c "isEmbeddablePath\|EMBEDDABLE_SHARE_ROUTE.test" src/helpers/frameGuard.ts` (=3: function decl :52, its use :54, guard call :70).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "setFrameGuardHeaders EMBEDDABLE_SHARE_ROUTE isLegacyHashShell frame-ancestors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the omit-don't-relax pattern and the redirect-hop rule; adapt the route regex to your share surface; omit the legacy-hash exemption once your embeds are canonicalized onto a dedicated prefix (upstream states the same plan). Coverage caveat: gui/global middleware specs are empty `describe` stubs at pin.
