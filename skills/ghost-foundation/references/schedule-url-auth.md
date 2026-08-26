<!-- capsule-v2 -->
# Schedule URL auth route — how does a scheduler ping authenticate without the 5-minute JWT cap?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** Why do schedule URLs need a separate auth path from normal Admin API tokens?

## authenticateWithUrl + route
**Path/Symbol:** `ghost/core/core/server/services/auth/api-key/admin.js:apiKeyAuthenticateWithUrl` (:69–81) consumed by `ghost/core/core/server/web/api/endpoints/admin/routes.js:94` (`router.put('/schedules/:resource/:id', mw.authAdminApiWithUrl, ...)`); controller `ghost/core/core/server/api/endpoints/schedules.js` (permissions :40–51; query :52–86).
**Signature:** `authenticateWithUrl(req, res, next)` → `wrappedAuthenticateWithToken(..., { token, ignoreMaxAge: true })`.
**Data Shape:** Token arrives as URL query `?token=`; validation options = defaults minus `maxAge` (audience/kid/HS256 checks unchanged).
### Decisive source
```js
// CASE: Scheduler publish URLs can have long maxAge but controllerd by expiry and neverBefore
return wrappedAuthenticateWithToken(req, res, next, { token, ignoreMaxAge: true });
```
**Flow:** GET/PUT `/schedules/:resource/:id?token=…` → extract token from `req.originalUrl` query (NOT Authorization header) → same kid→ApiKey→hex-secret→audience verification but `maxAge` omitted because exp/nbf in the token body already bound it to published_at (see scheduler-token-expiry-window capsule) → schedules controller runs publish ladder → responds 2xx with EMPTY list on no-op "so the scheduler treats the job as done and does not retry".
**Invariant:** The ignoreMaxAge bypass is safe ONLY because getSignedAdminToken sets exp/nbf explicitly; normal admin tokens keep `maxAge: '5m'`. Missing resource must 2xx-no-op at BOTH permission and query stages or the scheduler's retry loop would hammer a deleted post. Route registration is PUT with `mw.authAdminApiWithUrl` (3 occurrences of that middleware name in admin routes).
**Probe:** `grep -cF "ignoreMaxAge" ghost/core/core/server/services/auth/api-key/admin.js` → expect `4`; `grep -cF "router.put('/schedules/:resource/:id'" ghost/core/core/server/web/api/endpoints/admin/routes.js` → expect `1`; `grep -cF "err.errorType === 'NotFoundError'" ghost/core/core/server/api/endpoints/schedules.js` → expect `1`; direct tests: `grep -cF "shouldn't authenticate with JWT signed > 5min ago" ghost/core/test/unit/server/services/auth/api-key/admin.test.js` → expect `1` (proves the 5m cap exists for the normal path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "apiKeyAdminAuth Authorization Ghost header", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual extraction (header vs URL query) + explicit maxAge bypass for schedule URLs only. Adapt route shape; never widen the bypass to other endpoints.
