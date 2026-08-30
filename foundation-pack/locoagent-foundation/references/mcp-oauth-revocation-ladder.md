<!-- capsule-v2 -->
# Token revocation ladder — how do I revoke MCP OAuth tokens across RFC-compliant and non-compliant servers?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** In what order are refresh/access tokens revoked, which auth method is chosen, and what happens when the server rejects RFC 7009 client auth?

## Refresh-first revocation + 401 Bearer fallback + XAA discoveryState AS resolution
**Path/Symbol:** `src/services/mcp/auth.ts`: `revokeServerTokens` (:467-618), `revokeToken` (:381-459), auth-method selection (:503-517), step-up-preserving re-auth option (:578-617).
**Signature:** `revokeToken({serverName, endpoint, token, tokenTypeHint:'access_token'|'refresh_token', clientId?, clientSecret?, accessToken?, authMethod='client_secret_basic'})`; `revokeServerTokens(serverName, serverConfig, {preserveStepUpState=false})`.
**Data Shape:** best-effort end-to-end: per-token revocation failures are logged and CONTINUED; local storage cleared regardless of server-side outcome (:575-576).

### Decisive source
```ts
// Per RFC 7009, public clients should authenticate by including
// client_id in the request body, NOT via an Authorization header. ...
// As defensive programming, we:
// 1. First try the RFC 7009 compliant approach (client_id in body)
// 2. If we get a 401, retry with Bearer auth as a fallback for non-compliant servers
if (axios.isAxiosError(error) && error.response?.status === 401 && accessToken) {
  // RFC 6749 §2.3.1: must not send more than one auth method. The retry
  // switches to Bearer — clear any client creds from the body.
  params.delete('client_id'); params.delete('client_secret')
  await axios.post(endpoint, params, { headers: { ...headers, Authorization: `Bearer ${accessToken}` } })
}
// Revoke refresh token first (more important - prevents future access token generation) (:523)
// XAA/PRM topology: resolve the AS via persisted discoveryState.authorizationServerUrl,
// NOT serverConfig.url — token/revocation endpoints live on the AS host (:482-485)
const authMethod = (authMethods && !authMethods.includes('client_secret_basic')
                    && authMethods.includes('client_secret_post')) ? 'client_secret_post'
                   : 'client_secret_basic'   // prefer revocation_endpoint_auth_methods_supported, else token endpoint's list
```

**Flow:** read stored tokens by serverKey → metadata from AS (discoveryState-aware) → no revocation_endpoint ⇒ log and skip → revoke refresh token then access token (each individually caught) → ALWAYS clear local entry → if preserveStepUpState (re-auth flow), rewrite entry keeping stepUpScope + minimal discoveryState `{authorizationServerUrl, resourceMetadataUrl}` so the next performMCPOAuthFlow skips re-probing (:597-611 — also strips legacy bulky metadata fields so overflowed blobs recover #30337).
**Invariant:** The Bearer retry must STRIP body credentials (never two auth methods at once); "Clear Auth" default wipes everything while only explicit re-auth preserves step-up state.
**Probe:** `grep -nF "tokenTypeHint: 'refresh_token'" src/services/mcp/auth.ts | head -1` (`530:`) and `grep -n "params.delete('client_id')" src/services/mcp/auth.ts` (`446:`) and `grep -n "? 'client_secret_post'" src/services/mcp/auth.ts` (`516:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "revokeServerTokens", limit: 5 });
```

## Verdict
Adopt refresh-first ordering, compliant-first/Bearer-fallback with credential stripping, discoveryState-based AS resolution, and optional step-up preservation. Adapt storage APIs. Omit analytics events.
