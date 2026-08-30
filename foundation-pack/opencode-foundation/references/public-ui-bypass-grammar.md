<!-- capsule-v2 -->
# Public UI auth bypass grammar — how do you let credential-less browser flows fetch a few static assets from an authenticated server?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** When a server password is set, every request under the UI catch-all requires Basic auth — but the browser's `<link rel="manifest">` fetch does not carry app-managed credentials, so PWA install 401s (regression #25698). How do you open exactly the assets the browser needs without weakening auth for the rest of the surface?

## GET-only exact-path set at router level
**Path/Symbol:** `packages/opencode/src/server/shared/public-ui.ts` (whole, 12L: `PUBLIC_UI_PATHS` :4-8, `isPublicUIPath` :10-12) + `middleware/authorization.ts` (`authorizationRouterMiddleware` :101-116, bypass check :110) + `server.ts` (route-plane comment :130-136, `authOnlyRouterLayer` :136, `docRoute` :190-192, `uiRoute` :194-203).
**Signature:** `isPublicUIPath(method: string, pathname: string) → boolean`; `PUBLIC_UI_PATHS = Set<string>` of exactly three paths.
**Data Shape:** the set is `/site.webmanifest`, `/web-app-manifest-192x192.png`, `/web-app-manifest-512x512.png`. The bypass returns the effect UNCHANGED (no credential lookup at all) — it is not "auth with empty credentials".

### Decisive source
```ts
// shared/public-ui.ts — the whole grammar is a method gate + exact-set membership:
// Static UI assets the browser fetches without app-managed credentials, e.g.
// the manifest link in <head>. These bypass auth so the page can install/render
// the manifest icons even when a server password is configured.
export const PUBLIC_UI_PATHS = new Set<string>([
  "/site.webmanifest",
  "/web-app-manifest-192x192.png",
  "/web-app-manifest-512x512.png",
])
export function isPublicUIPath(method: string, pathname: string) {
  return method === "GET" && PUBLIC_UI_PATHS.has(pathname)
}
// middleware/authorization.ts:108-113 — applied ONLY in the raw router middleware:
const request = yield* HttpServerRequest.HttpServerRequest
const url = new URL(request.url, "http://localhost")
if (isPublicUIPath(request.method, url.pathname)) return yield* effect
return yield* credentialFromURL(url, request).pipe(
  Effect.flatMap((credential) => validateRawCredential(effect, credential, config)),
)
```

**Flow:** The bypass lives in `authorizationRouterMiddleware`, the RAW router-level middleware that only `docRoute` and `uiRoute` receive (`authOnlyRouterLayer`, server.ts :136/:191/:203). The typed-API tiers (`authorizationLayer` for instance routes, `serverAuthorizationLayer` for /api/*) never call `isPublicUIPath` — so the bypass cannot leak into the API surface. The check itself is two conjuncts: method must be GET (a POST to /site.webmanifest still authenticates) and pathname must be an exact member of the three-path Set (no prefix matching, no query tolerance — the pathname comes from `new URL(...)` so queries are already stripped). The route-plane comment (server.ts :135) states the design reason: "uiRoute: raw catch-all fallback; auth is router middleware so public static assets can bypass it." Separately, CORS preflight OPTIONS requests are allowed without auth by the cors middleware ordering (test pins 204 + origin echo), which is why the manifest's cross-origin setup works end-to-end.
**Invariant:** The credential-less surface is exactly {GET} × {three asset paths}, evaluated at the only middleware layer that sees raw catch-all routes. Any new public asset must be added to the Set explicitly; there is no wildcard, no directory, no content-type-based bypass. Auth-disabled servers short-circuit before any of this (the middleware returns the identity function when no password is configured).
**Probe:** `packages/opencode/test/server/httpapi-ui.test.ts:424-441` ("serves the PWA manifest without auth even when a server password is set" — regression #25698 comment block — pins all three paths return non-401 with password "secret" configured); `:443-456` ("allows web UI preflight without auth" pins OPTIONS → 204 with `access-control-allow-origin` echo); `:396-422` pins Basic auth accepted for `/` including passwords containing colons); source pin:
```bash
grep -n 'method === "GET" && PUBLIC_UI_PATHS.has(pathname)' packages/opencode/src/server/shared/public-ui.ts
grep -n 'isPublicUIPath(request.method' packages/opencode/src/server/routes/instance/httpapi/middleware/authorization.ts
```
expect 1 + 1 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "isPublicUIPath PUBLIC_UI_PATHS authorizationRouterMiddleware uiRoute docRoute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the narrow-set-at-the-right-layer pattern for any authenticated server that must serve browser-initiated credential-less fetches: an explicit path Set plus a method gate, placed in the middleware layer that actually sees those routes (raw router level for catch-all static serving), never in shared typed-API auth. Keep the bypass as "skip credential lookup entirely" rather than "accept empty credentials" so logging/audit semantics stay clean. Adapt the asset list to your PWA/static surface; omit the pattern entirely if your UI is same-origin behind a login page instead of a server password. Direct test read whole (httpapi-ui.test.ts 457L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
