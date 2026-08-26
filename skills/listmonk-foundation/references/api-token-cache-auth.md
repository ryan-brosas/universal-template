<!-- capsule-v2 -->
# api-token-cache-auth — How are API requests authenticated and why does cookie presence beat BasicAuth?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What is the middleware auth order, token storage shape, and permission check?

## Cached-user constant-time tokens + cookie precedence
**Path/Symbol:** `internal/auth/auth.go` — Middleware (:288-336), GetAPIToken (:138-149), HashAPIToken (:398-401), parseAuthHeader (:440-472), Perm (:338-366), session prune goroutine (:113-117).
**Signature:** `Authorization: token api_key:access_token` OR legacy `Basic base64(api_key:access_token)`; `HashAPIToken = hex(sha256(token))`.
**Data Shape:** users cached map[username]User refreshed wholesale via CacheAPIUsers / individually via CacheAPIUser; sessions in Postgres via simplesessions.

### Decisive source
```go
// Cookie presence DISABLES header auth (v3→v4 upgrade compatibility):
if c := strings.TrimSpace(c.Request().Header.Get("Cookie")); strings.Contains(c, "session=") {
	hdr = ""
}
...
if !ok || subtle.ConstantTimeCompare([]byte(t.Password.String), []byte(HashAPIToken(token))) != 1 {
	return User{}, false
}
...
// Perm: Super Admin bypasses all checks
if u.UserRole.ID == SuperAdminRoleID { return next(c) }
```

**Flow:** middleware: cookie-with-session ⇒ header ignored entirely (stale browser BasicAuth caused redirect loops post-upgrade — upstream TODO to remove) → parseAuthHeader accepts token-scheme then Basic fallback, rejecting empty halves → lookup cached user by api_key → sha256 the presented token and ConstantTimeCompare against stored digest (tokens hashed at rest; cache holds digests) → failure stores an *echo.HTTPError IN CONTEXT and calls next(c) anyway; each route group's wrapper decides JSON-error vs login-redirect. Perm middleware then checks ANY-of listed permissions unless superadmin.
**Invariant:** Auth failures are DEFERRED (context-stashed), not returned — one middleware serves both browser (redirect) and API (JSON) surfaces. Token comparison must be constant-time over hashes, never plaintext. Cache invalidation is push-based on user save; a porter who reads users per-request loses the O(1) path but gains freshness — document the trade.
**Probe:** `bash -c "cd <repo> && grep -nF 'strings.Contains(c, \"session=\")' internal/auth/auth.go"` → :300; `grep -cF 'sha256.Sum256([]byte(token))' internal/auth/auth.go` → 1; `grep -cF 'SuperAdminRoleID' internal/auth/auth.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "GetAPIToken Middleware", limit: 10 });
```
## Verdict
Adopt deferred-failure auth middleware + hashed constant-time API tokens. Adapt session store freely. Omit OIDC flow (separate seam, standard library usage).
