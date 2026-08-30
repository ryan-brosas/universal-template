<!-- capsule-v2 -->
# OAuth2 token lifecycle ladder — when do you reuse, refresh, refetch, or ship an expired token?

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** Given stored credentials + `autoFetchToken`/`autoRefreshToken` flags, what is the exact decision ladder a client runs before sending a request — and what must never be sent stale?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/auth/oauth2-helper.ts:getOAuth2Token` (:319-399), `isTokenExpired` (:305); twin full-ladder implementations in `packages/bruno-electron/src/utils/oauth2.js` (:139+ authorization-code, client-credentials, password variants) and CLI twin `packages/bruno-cli/src/utils/oauth2.js`.
**Signature:** `getOAuth2Token(oauth2Config: OAuth2Config, tokenStore: TokenStore, verbose: string, axiosInstance?) → Promise<string | null>`.
**Data Shape:** `TokenStore = { saveCredential({url, credentialsId, credentials}), getCredential({url, credentialsId}), deleteCredential(...) }` — all keyed by `(accessTokenUrl, credentialsId='default')`. Credentials object carries `access_token`, optional `expires_in`, `created_at` (stamped at fetch), optional `refresh_token`, `id_token`.

### Decisive source
```ts
const isTokenExpired = (credentials: any): boolean => {
  if (!credentials?.access_token) return true;
  if (!credentials?.expires_in || !credentials.created_at) {
    return false; // No expiration info, assume valid
  }
  const expiryTime = credentials.created_at + credentials.expires_in * 1000;
  return Date.now() > expiryTime;
};
```

**Flow (the ladder, identical in electron/CLI twins):** load stored by `(url, credentialsId)` → valid ⇒ return token (`tokenSource === 'id_token'` picks `id_token`) → expired ⇒ if `autoRefreshToken && refresh_token`: try refresh; on refresh failure CLEAR store then fall through (`autoFetchToken ? fetch new : return expired`) → else-if `autoFetchToken` clear + fetch new → else **return the expired token** (explicit user opt-out beats freshness). No stored creds ⇒ `autoFetchToken ? fetch : null`.
**Invariant:** expiry math is `created_at + expires_in*1000` with missing-expiry-data ⇒ treat as valid (never refetch on servers that omit `expires_in`); a failed refresh ALWAYS clears the poisoned `refresh_token` before any fallback; every grant validates required fields first and throws typed errors naming the field. Electron variant returns `{collectionUid, url, credentials, credentialsId, debugInfo}` data-shaped errors instead of throwing for validation misses.
**Probe:** `packages/bruno-requests/src/auth/oauth2-helper.spec.ts` :67-475 — axios-mocked grant requests pinning Basic-header vs body placement per `credentialsPlacement` (incl. empty-secret still sends header with `clientSecret ?? ''`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "getOAuth2Token isTokenExpired tokenStore", limit: 5 });
// resolves both helper and electron twins line-exact (:305-314 / :41-50)
```

## Verdict
Adopt the four-flag ladder verbatim — its ordering (valid > refresh > refetch > expired-but-requested) is the portable contract. Adapt the TokenStore to your persistence; omit Bruno's debug-info envelope. Coverage caveat: none — paths report clean coverage.
