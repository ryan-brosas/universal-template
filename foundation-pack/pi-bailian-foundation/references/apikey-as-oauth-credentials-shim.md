<!-- capsule-v2 -->
# API-key-as-OAuth-credentials shim — how does a static API key satisfy an OAuth-shaped credential interface without a token server?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** Where do I put a non-expiring API key when the host insists on OAuth credentials with refresh semantics?

## Credential storage + no-op refresh seam
**Path/Symbol:** `src/index.ts:loginBailian` (:103-107), `getApiKey` (:120-122), `refreshBailianToken` (:128-134).
**Signature:** `function getApiKey(credentials: OAuthCredentials): string`; `async function refreshBailianToken(credentials: OAuthCredentials): Promise<OAuthCredentials>`.
**Data Shape:** `OAuthCredentials{refresh, access, expires}`; the SAME key string is written into both `refresh` and `access`; `expires = Date.now() + 365*24*60*60*1000`.

### Decisive source
```ts
  // Return credentials (stored in auth.json)
  return {
    refresh: apiKey, // Re-use 'refresh' field to store the API key
    access: apiKey, // Also store in 'access' for compatibility
    expires: Date.now() + 365 * 24 * 60 * 60 * 1000, // 1 year expiry
  };
...
async function refreshBailianToken(credentials: OAuthCredentials): Promise<OAuthCredentials> {
  // API keys don't expire, but extend the expiry date to keep credentials valid
  return {
    ...credentials,
    expires: Date.now() + 365 * 24 * 60 * 60 * 1000, // 1 year from now
  };
}
...
function getApiKey(credentials: OAuthCredentials): string {
  return credentials.access || credentials.refresh;
}
```

**Flow:** login validates key → writes `{refresh: key, access: key, expires: +1y}` → host persists to auth.json → whenever the host decides creds look stale, `refreshToken` returns the spread of existing credentials with only `expires` pushed forward.
**Invariant:** refresh NEVER mutates key material (`...credentials` spread keeps `refresh`/`access` byte-identical); it exists purely to keep the host's expiry check satisfied. `getApiKey` reads `access || refresh`, so either slot alone is sufficient — the read-side twin of the dual-slot write. Note both handlers are host-invoked callbacks with ZERO in-graph callers (CALLS census re-run at pin: only loginBailian→validateApiKey and loginBailianCN→loginBailian exist).
**Probe:** `test/exports.test.ts` (module surface) + README auth-file shape :99-108 (`"type":"oauth"` with both fields holding `sk-sp-…`) — direct-test runner BLOCKED this pass (no node_modules; vitest unexecutable in read-only checkout); line-pinned source anchors stand in.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "OAuth credentials store api key refresh access expires", limit: 5, fields: ["signature", "lines"] });
```
Executed live at pin: returned `validateApiKey` (42-62), `getApiKey` (120-122), test-local `validateApiKey` (14-34), `refreshBailianToken` (128-134) — total 4, has_more false.

## Verdict
Adopt the dual-slot write plus expiry-only refresh as the portable shim for any host whose provider config demands OAuth-shaped credentials. Adapt the expiry horizon and field names to your host's persistence schema. Omit real token-server logic — there is none here by design.
