<!-- capsule-v2 -->
# XAA silent exchange in tokens() — how does a cached IdP id_token make MCP re-auth zero-interaction?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When does `ClaudeAuthProvider.tokens()` fire the XAA chain instead of returning stored tokens, and what are the failure semantics?

## Auto-auth branch gated on no-refresh-token + ≤300s expiry
**Path/Symbol:** `src/services/mcp/auth.ts`: auto-auth branch (:1585-1615), `xaaRefresh` (:1751-1850), promise-dedupe field `_refreshInProgress` shared with the normal refresh path; XaaTokenExchangeError.shouldClearIdToken (xaa.ts :77-84).
**Signature:** branch condition: `isXaaEnabled() && serverConfig.oauth?.xaa && !tokenData?.refreshToken && (!tokenData?.accessToken || (tokenData.expiresAt - Date.now())/1000 <= 300)`.
**Data Shape:** xaaRefresh returns `undefined` (NOT throw) when id_token isn't cached or config vanished — caller falls through to needs-auth; throws only on exchange failure with shouldClearIdToken semantics.

### Decisive source
```ts
// Fires on:
//   - never authed (!tokenData)                 → first connect, auto-auth
//   - SDK partial write {accessToken:''}        → stale from past session
//   - expired/expiring, no refresh_token        → proactive XAA re-auth
//
// No special-casing of {accessToken:'', expiresAt:0}. ... guarding on `!==''`
// permanently bricks auto-auth when a *prior* session left that marker
// in keychain — real bug seen with xaa.dev.  (:1570-1579)
if (!this._refreshInProgress) {
  this._refreshInProgress = this.xaaRefresh().finally(() => { this._refreshInProgress = undefined })
}
try { const refreshed = await this._refreshInProgress; if (refreshed) return refreshed }
catch (e) { /* logged, fall through */ }
// Fall through: !tokenData → undefined → 401 → needs-auth; expired → same.
// Only fire when we don't have a refresh_token. If the AS returned one,
// the normal refresh path is cheaper — 1 request vs the 4-request XAA chain.
```

**Flow:** SDK requests tokens → xaa-configured + no refresh token + missing/expiring access token → dedupe via instance promise → cached id_token? → discoverOidc(IdP) soft-fail to undefined → performCrossAppAccess (4-request chain) → write storage DIRECTLY (not saveTokens) so clientId+clientSecret land even on first write — otherwise revokeServerTokens later reads clientId as undefined and sends a client_id-less RFC 7009 request that strict ASes reject (:1804-1808 comment). Exchange failure with 4xx/invalid body ⇒ clear cached id_token (next attempt = fresh IdP login); 5xx ⇒ preserve it.
**Invariant:** The empty-string accessToken marker must NOT be special-cased (bricks auto-auth across sessions); xaaRefresh must soft-return undefined rather than throw for cache-miss/config-gone so connect degrades to needs-auth instead of erroring mid-connect. Cross-process dedupe is explicitly TODO (`_refreshInProgress` is per-process; GA requires mirroring refreshAuthorization's lockfile pattern :1743-1749).
**Probe:** `grep -n '(tokenData.expiresAt - Date.now()) / 1000 <= 300' src/services/mcp/auth.ts` (`1590:`) and `grep -n 'this._refreshInProgress = this.xaaRefresh()' src/services/mcp/auth.ts` (`1599:`) and `grep -n 'readonly shouldClearIdToken: boolean' src/services/mcp/xaa.ts` (`78:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ClaudeAuthProvider", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "performCrossAppAccess", limit: 5 });
```

## Verdict
Adopt the trigger predicate, soft-undefined degradation, direct-storage write, and clear-on-4xx id_token hygiene. Adapt IdP settings plumbing (xaaIdpLogin plane omitted-with-reason). Omit analytics fields.
