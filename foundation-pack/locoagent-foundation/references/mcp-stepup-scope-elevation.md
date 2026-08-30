<!-- capsule-v2 -->
# Step-up scope elevation — how do I add scope to an existing MCP OAuth grant when RFC 6749 forbids elevation via refresh?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Why must `tokens()` hide the refresh token during a step-up, and where does the requested scope get detected and persisted?

## 403 insufficient_scope detection → omit refresh_token → PKCE re-consent → persist scope
**Path/Symbol:** `src/services/mcp/auth.ts`: `wrapFetchWithStepUpDetection` (:1354-1374), `markStepUpPending` (:1468-1471), needsStepUp computation (:1625-1637), conditional omission `refresh_token: needsStepUp ? undefined : tokenData.refreshToken` (:1688-1694), saveTokens resets pending (:1704-1705), persistence gate `if (this._scopes && !this.handleRedirection)` (:1890-1900).
**Signature:** wrapper composed INNERMOST: `fetch: wrapFetchWithTimeout(wrapFetchWithStepUpDetection(createFetchWithInit(), authProvider))` — ordering matters so the 403 is seen before the SDK's handler calls auth()→tokens().
**Data Shape:** WWW-Authenticate scope match `/scope=(?:\"([^\"]+)\"|([^\s,]+))/` accepts quoted AND unquoted values (RFC 6750 §3).

### Decisive source
```ts
// Wraps fetch to detect 403 insufficient_scope responses and mark step-up
// pending on the provider BEFORE the SDK's 403 handler calls auth(). Without
// this, the SDK's authInternal sees refresh_token → refreshes (uselessly, since
// RFC 6749 §6 forbids scope elevation via refresh) → returns 'AUTHORIZED' →
// retry → 403 again → aborts with "Server returned 403 after trying upscoping",
// never reaching redirectToAuthorization where step-up scope is persisted.
// With this flag set, tokens() omits refresh_token so the SDK falls through
// to the PKCE flow. See github.com/anthropics/claude-code/issues/28258.
const currentScopes = tokenData.scope?.split(' ') ?? []
const needsStepUp =
  this._pendingStepUpScope !== undefined &&
  this._pendingStepUpScope.split(' ').some(s => !currentScopes.includes(s))
```

**Flow:** request → 403 with insufficient_scope → wrapper parses scope, provider.markStepUpPending → SDK asks tokens() → current token lacks a requested scope ⇒ return tokens WITHOUT refresh_token → SDK skips refresh, runs startAuthorization → redirectToAuthorization captures new scopes from the URL → because handleRedirection=false (transport-attached provider), persists `stepUpScope` into secure storage → next full performMCPOAuthFlow reads cachedStepUpScope instead of probing (:903-935).
**Invariant:** The proactive-refresh branch is skipped when needsStepUp (:1650); refreshing can never elevate scope so it must be suppressed on BOTH paths. Only persist step-up scope from the transport-attached provider — persisting during interactive flows would store metadata-derived scope as if a 401 demanded it.
**Probe:** `grep -n 'provider.markStepUpPending(scope)' src/services/mcp/auth.ts` (`1368:`) and `grep -n 'refresh_token: needsStepUp ? undefined : tokenData.refreshToken,' src/services/mcp/auth.ts` (`1690:`) and `grep -n 'existing.stepUpScope = this._scopes' src/services/mcp/auth.ts` (`1896:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "wrapFetchWithStepUpDetection", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ClaudeAuthProvider", limit: 5 });
```

## Verdict
Adopt innermost-wrapper detection, refresh-token omission during step-up, and transport-side scope persistence. Adapt storage keys. Omit issue-number references beyond provenance.
