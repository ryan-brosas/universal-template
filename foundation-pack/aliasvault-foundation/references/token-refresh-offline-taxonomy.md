<!-- capsule-v2 -->
# Token-refresh offline taxonomy — which failures log the user out and which must fall back to offline mode?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** How does an API wrapper distinguish "session dead" from "server unreachable" during token refresh?

## Three-way refresh outcome
**Path/Symbol:** `apps/browser-extension/src/utils/WebApiService.ts:370-420` (`refreshAccessToken`), :59-127 (`authFetch` retry ladder), :319-347 (`getStatus` offline shape).
**Signature:** `private async refreshAccessToken(): Promise<{ token: string | null; isAuthError: boolean }>`.
**Data Shape:** Timeouts: 5s default, 180s for vault transfers (`buildTimeoutSignal`: endpoint `vault` or `Accept: application/octet-stream`); server rejects outdated clients with HTTP 426 ⇒ `ClientUpgradeRequiredError` on ANY endpoint.

### Decisive source
```ts
// Auth errors (401/403) mean session is truly expired
if (response.status === 401 || response.status === 403) {
  return { token: null, isAuthError: true };
}
// Server errors (5xx) or other non-auth errors, treat as offline/transient
console.warn(`Token refresh failed with status ${response.status}, treating as offline`);
return { token: null, isAuthError: false };
```
```ts
// authFetch: after a SUCCESSFUL refresh only 401/403 mean session-invalid:
if (retryResponse.status === 401 || retryResponse.status === 403) {
  throw new ApiAuthError('Request failed after token refresh');
}
```

**Flow:** request → 401 → refresh via `Auth/refresh` → success: swap tokens + retry once → refresh 401/403 OR no stored refresh token ⇒ emit logout (`logoutEventEmitter.emit('common.errors.sessionExpired')`) → refresh network/5xx ⇒ throw NetworkError so callers enter OFFLINE mode keeping credentials → getStatus maps any non-auth failure to a synthetic `{ serverVersion: '0.0.0', ... }` offline status while persisting the last real version for settings display.
**Invariants:** (1) Only AUTH failures destroy the session; transient server errors never log users out. (2) Refresh requests are single-shot — no nested refresh loops. (3) The offline status sentinel is exactly `serverVersion: '0.0.0'`. (4) Timeout vs network errors are distinct types (`RequestTimeoutError` on DOMException Abort/Timeout, else `NetworkError`). (5) 426 upgrade-required propagates as its own class even through refresh's catch.
**Probe:** `grep -c 'isLargeTransfer' apps/browser-extension/src/utils/WebApiService.ts` → `2`; `grep -c 'treating as offline' apps/browser-extension/src/utils/WebApiService.ts` → `2`; `grep -c 'ClientUpgradeRequiredError' apps/browser-extension/src/utils/WebApiService.ts` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "refreshAccessToken", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the {success | auth-error⇒logout | transport-error⇒offline} triad with one-retry budget; adapt error classes; omit wxt storage plumbing. Source confirmed at pin `95903e92`.
