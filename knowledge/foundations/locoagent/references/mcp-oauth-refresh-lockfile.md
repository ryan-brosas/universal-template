<!-- capsule-v2 -->
# Cross-process refresh lockfile — how do multiple CLI instances refresh the same MCP OAuth token without burning it?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the correct lock-and-recheck dance around a single-use refresh token shared across processes?

## Lock → re-read storage → adopt winner → refresh only if still stale
**Path/Symbol:** `src/services/mcp/auth.ts`:`ClaudeAuthProvider.refreshAuthorization` (:2090-2175) + `_doRefresh` (:2177-2359); lock path `join(claudeDir, 'mcp-refresh-${sanitizedKey}.lock')` (:2094-2097, sanitized `serverKey.replace(/[^a-zA-Z0-9]/g,'_')`); `MAX_LOCK_RETRIES = 5` (:94).
**Signature:** `refreshAuthorization(refreshToken: string): Promise<OAuthTokens | undefined>`; ELOCKED backoff `await sleep(1000 + Math.random() * 1000)`; lock failure after retries PROCEEDS UNLOCKED (availability over mutual exclusion, logged :2131-2136).
**Data Shape:** freshness threshold `expiresIn > 300` seconds — same 5-minute window that triggers proactive refresh in tokens().

### Decisive source
```ts
try {
  // Re-read tokens after acquiring lock — another process may have refreshed
  clearKeychainCache()
  const tokenData = data?.mcpOAuth?.[serverKey]
  if (tokenData) {
    const expiresIn = (tokenData.expiresAt - Date.now()) / 1000
    if (expiresIn > 300) {
      logMCPDebug(serverName, `Another process already refreshed tokens (...)`)
      return { access_token: tokenData.accessToken, ... }        // ADOPT, don't re-refresh
    }
    if (tokenData.refreshToken) refreshToken = tokenData.refreshToken  // freshest RT from storage
  }
  return await this._doRefresh(refreshToken)
} finally { await release() /* logged best-effort */ }
// _doRefresh InvalidGrantError arm: clearKeychainCache() then RE-CHECK storage
// for expiresIn > 300 before invalidating — the loser of a race sees invalid_grant
// because the winner already consumed the old refresh token (:2289-2325). The
// adopted-tokens return deliberately does NOT emit success telemetry: "the winning
// process already emitted its own success event. Emitting here would double-count." (:2305-2308)
```

**Flow:** proactive-refresh trigger (≤300s left) → acquire per-server lockfile (jittered retry on ELOCKED) → clear keychain cache → fresh read → someone newer? adopt their tokens → else use the FRESHEST stored refresh token (another process may have rotated it since our caller read it) → SDK refreshAuthorization → saveTokens → release. Retry ladder in _doRefresh: timeout/ServerError/TemporarilyUnavailable/TooManyRequests are retryable ×3 with 1s/2s/4s backoff (:2327-2354).
**Invariant:** NEVER refresh using the caller's stale copy when storage holds a newer one; never invalidate tokens on invalid_grant without re-reading storage first — a lost race looks exactly like a revoked token.
**Probe:** `grep -nF 'mcp-refresh-' src/services/mcp/auth.ts | head -1` (`2097:`) and `grep -c 'expiresIn > 300' src/services/mcp/auth.ts` (`2` — pre-refresh adopt check AND post-invalid-grant re-check) and `grep -n 'Math.random() \\* 1000' src/services/mcp/auth.ts | head -1` (`2121:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ClaudeAuthProvider", limit: 5 });
// refreshAuthorization resolves as auth.ClaudeAuthProvider.refreshAuthorization line-exact
```

## Verdict
Adopt lock→recheck→adopt-or-refresh and the invalid_grant storage-recheck. Adapt lockfile library and thresholds. Omit telemetry double-count bookkeeping.
